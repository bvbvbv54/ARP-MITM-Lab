# ARP-MITM-Lab

![ARP-MITM-Lab banner](assets/banner.svg)

**A visual guide to ARP, local network trust, and defensive investigation in an isolated VirtualBox lab.**

![Python](https://img.shields.io/badge/Python-3.9%2B-00E676?logo=python&labelColor=20262d) ![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-00D9FF?logo=powershell&labelColor=20262d) ![Linux](https://img.shields.io/badge/Linux-Parrot%20OS-00E676?logo=linux&labelColor=20262d) ![Windows](https://img.shields.io/badge/Windows-11-00D9FF?logo=windows11&labelColor=20262d) ![VirtualBox](https://img.shields.io/badge/VirtualBox-isolated%20network-FFB020?labelColor=20262d) ![Networking](https://img.shields.io/badge/Networking-ARP%20%2F%20IPv4-FF4D6D?labelColor=20262d)

> **Authorized lab only.** ARP manipulation can redirect or interrupt other devices on a shared link. Use only systems and networks you own or have explicit permission to test. See [DISCLAIMER.md](DISCLAIMER.md).

## The lesson in one minute

An IPv4 packet destined outside a local subnet goes to a **default gateway**. The host first needs the gateway interface's **MAC address** to deliver an Ethernet frame on the current link. ARP supplies that IPv4-to-MAC mapping. Because ordinary ARP replies are not authenticated, a false claim can change a host's neighbor cache. A changed cache entry shows a changed local delivery decision; it **does not alone prove** that traffic was intercepted.

This guide was built from the existing local `scripts/arp_lab.py` and read-only `scripts/win11_probe.ps1`. The operational scripts are **not distributed in this public documentation repository**; both originals remain unchanged in the source workspace. The diagrams use **illustrative documentation addresses**, not recorded lab measurements. No packet captures or completed run logs were supplied.

## What you will learn

- How IPv4, Ethernet, MAC addresses, gateways, and ARP fit together.
- Why a false gateway mapping can redirect or interrupt local traffic.
- What the three existing script modes intend to demonstrate, and what evidence would verify each outcome.
- Why interface inspection, neighbor caches, ping, and Nmap can show different sets of hosts.
- How to check gateway mappings and reduce ARP poisoning risk.

## Network map

![Normal communication between Windows, gateway, and an external service](assets/diagrams/normal-network.svg)

The Windows host sends off-subnet IPv4 traffic to the gateway's MAC on the **local link**. The gateway then routes the IP packet onward using a new link-layer frame. See [network topology and isolation](docs/06-network-topology.md).

**Explore the path:** [Download the interactive explainer](assets/interactive-network.html) and open it locally in a browser. Its three buttons switch the victim's mapping and frame path; it sends no network traffic. GitHub previews HTML as source, so open the downloaded file for the interaction.

<details>
<summary>Show the three states here on GitHub</summary>

1. **Normal:** gateway IP maps to the genuine gateway MAC; local frame goes to the gateway.
2. **Changed mapping:** the same gateway IP maps to the lab VM MAC; data can reach the gateway only if forwarding works.
3. **No forwarding:** the victim still sends to the lab VM, but delivery onward may stop.

</details>

## The trust boundary

![Gateway mapping before and after a misleading ARP claim](assets/diagrams/arp-cache-comparison.svg)

A false ARP claim can make the victim address its local Ethernet frames to a different MAC. [The MITM diagram](assets/diagrams/mitm-topology.svg) distinguishes those ARP messages from forwarded data. Transparent forwarding requires a working relay path; a cache change alone is insufficient.

## Existing lab modes

| Mode | Implemented concept | Evidence needed to claim the outcome |
| --- | --- | --- |
| `mitm` | Bidirectional claims to victim and gateway, IPv4 forwarding, packet counters | Paired neighbor-cache changes and corroborated traffic flow through the lab host |
| `takeover` | One-way gateway claim to victim, without enabling forwarding | Incorrect victim mapping plus a time-matched reachability failure and healthy gateway checks |
| `flood` | Repeated forged ARP claims for addresses in the gateway's `/24` prefix | Time-matched cache and capture observations; the script itself does not prove table overflow |

These are **source-code behaviors**, not verified experimental results. The source includes restoration attempts on normal teardown, but abrupt termination or link failure can leave a stale entry. [Mode details](docs/03-laboratory-modes.md) explain the limits.

## Read-only investigation

| Linux / Parrot OS | Windows 11 | Question answered |
| --- | --- | --- |
| `ip -br addr`, `ip link show` | `ipconfig /all` | Which addresses and interfaces are configured here? |
| `ip route` | `route print` | Which route and gateway would this host use? |
| `ip neigh` | `arp -a` | Which local IPv4-to-MAC mappings are cached? |
| `cat /sys/class/net/<interface>/address` | `Get-NetAdapter` | What MAC is currently exposed for this local interface? |

These commands answer different questions. `ip addr` is **local configuration**, `ip neigh` is a **cache**, ping is a **reachability probe**, and Nmap host discovery actively tests an **authorized scope**. A silent host need not be offline. VirtualBox's ordinary per-VM NAT does not automatically put VMs on a shared Layer 2 segment. [Host discovery guide](docs/02-host-discovery.md) explains the differences.

## Defend and verify

Compare the observed gateway MAC with a trusted baseline. Use time-matched neighbor tables, packet captures, and connectivity checks to separate a suspicious mapping from ordinary cache changes or a router outage. On supported managed switches, Dynamic ARP Inspection can validate ARP against trusted bindings. TLS protects application data in transit but does not stop ARP cache changes. See [defense and mitigation](docs/05-defense-and-mitigation.md).

## Read the masterclass

1. [Network foundations](docs/01-network-foundations.md)
2. [Host discovery and VirtualBox](docs/02-host-discovery.md)
3. [What the existing modes implement](docs/03-laboratory-modes.md)
4. [Windows victim observations](docs/04-victim-observations.md)
5. [Defense and mitigation](docs/05-defense-and-mitigation.md)
6. [Network topology and evidence boundaries](docs/06-network-topology.md)
7. [Glossary](docs/glossary.md)
8. [Results and evidence template](results/README.md)

## Repository map

```text
README.md                     Start here
docs/                         Concept lessons and evidence guidance
assets/                       Local SVG illustrations
assets/interactive-network.html  Self-contained interactive concept
results/README.md             Blank, clearly labeled results template
DISCLAIMER.md                 Scope and isolation
SECURITY.md                   Reporting and publication hygiene
```

## Scope and attribution

The original scripts remain in their local `scripts/` directory, byte-for-byte. This documentation does not assert a successful interception, outage, packet rate, or host-discovery result without a saved observation. No license was added: ownership and redistribution rights for the existing code were not established. Educational references: [VirtualBox networking guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/networkingdetails.html), [Nmap host discovery](https://nmap.org/book/man-host-discovery.html), and [Cisco Dynamic ARP Inspection](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst3560/software/release/15-0_2_se/configuration/guide/scg3560/swdynarp.html).
