# 03 — Implemented laboratory modes

[Start](../README.md) · [Victim measurements](04-victim-observations.md)

I implemented three modes in my local `scripts/arp_lab.py` and successfully tested ARP poisoning in MITM mode. The **victim** is my Windows 11 host; the **gateway** is its next hop for off-subnet IPv4 traffic; the **lab host** is my Parrot OS VM. The saved console and neighbor-cache screenshots show `enp0s3`, `10.0.2.1`, `10.0.2.6`, and `10.0.2.15` in this run. The Python implementation remains local; the read-only [Windows observer](../scripts/win11_probe.ps1) is in the public checkout.

![Normal and manipulated paths](../assets/diagrams/mitm-topology.svg)

*Red arrows represent misleading ARP claims. Cyan arrows represent data frames. The artwork explains the implemented path; its addresses are illustrative.*

ARP's weak trust model permits an IP-to-MAC claim without cryptographic proof. The script first attempts to resolve victim and gateway MACs. Its ordinary teardown sends corrective ARP frames and restores the prior IPv4-forwarding setting when that prior value is readable. An abrupt kill or failed delivery can prevent complete recovery; verify the peers afterward.

| Mode | Implemented behavior | Security lesson |
| --- | --- | --- |
| `mitm` | Claims each peer's IP at the lab host MAC, enables IPv4 forwarding, and counts sniffed packets | Two-sided cache manipulation plus forwarding can redirect a local flow |
| `takeover` | Sends a gateway claim to the victim without enabling forwarding | A wrong next-hop MAC can interrupt delivery even while the router remains healthy |
| `flood` | Sends repeated forged claims for addresses in the gateway's `/24` prefix | Neighbor state and control traffic require careful measurement |

### MITM mode

The MITM mode implements bidirectional claims, forwarding, and a sniffer thread that counts packets by protocol and peer IP. I ran this mode in the successful poisoning experiment. My console screenshot shows `forward=1` and nonzero counters, while Windows shows the changed gateway MAC. The counters measure frames visible to the sniffer; they are not a measure of decrypted application content.

### Takeover mode

The victim can receive an incorrect gateway mapping and send frames toward an interface that does not relay them. The gateway itself can remain available to other hosts. Compare victim cache, route, and gateway reachability with another unaffected machine to separate a local mapping fault from a router outage. Takeover mode does not enable forwarding, although it does not force an already-enabled system setting off.

![Incorrect mapping and connectivity disruption](../assets/diagrams/takeover-concept.svg)

*Red is the wrong cached mapping. Amber indicates traffic that can fail to reach the gateway.*

### Flood mode

Flood mode generates repeated forged ARP replies for IPv4 addresses derived from the gateway's first three octets. It starts a flood worker and reporter, **not the sniffer worker**; its packet counters therefore do not measure received traffic volume in this mode. It enables forwarding, but the selected workers do not run the normal bidirectional poison loop. Cache acceptance and capacity depend on the victim. Time-matched ARP captures, neighbor entries, and connectivity measurements show the effect in an isolated lab.

![Repeated ARP claim concept](../assets/diagrams/arp-flood-concept.svg)

*Repeated claims are control traffic, not proof that the victim accepted each mapping.*

## My test result

**ARP poisoning passed:** the Windows gateway association changed to my lab host MAC; Wireshark displayed the relevant ARP traffic; and MITM mode ran with forwarding enabled and traffic visible to its counters. I have not presented takeover or flood as separately tested outcomes. [Testing notes](../results/README.md) record the observations, and the [screenshot gallery](../assets/screenshots/README.md) is ready for the genuine captures.
