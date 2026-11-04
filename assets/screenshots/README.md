# Laboratory screenshot gallery

[Back to project](../../README.md)

This directory is reserved for **genuine screenshots from my completed lab**. I will add publication-safe images here and embed each one beside its explanation in the main README. The diagrams elsewhere in the repository are illustrations, not substituted captures.

| Suggested file | What it should show | README placement |
| --- | --- | --- |
| `01-parrot-network.png` | Parrot OS interface and IPv4 configuration | How I investigated the network |
| `02-interface-mac.png` | MAC read from `/sys/class/net/<interface>/address` | How I investigated the network |
| `03-default-gateway.png` | `ip route` default gateway | Laboratory architecture |
| `04-arp-before.png` | Genuine gateway mapping before the run | ARP poisoning |
| `05-arp-after.png` | Changed gateway mapping during the run | ARP poisoning |
| `06-wireshark-arp.png` | ARP replies and duplicate-IP analysis | Laboratory testing |
| `07-windows-victim.png` | Windows neighbor and connectivity observations | Windows victim |
| `08-mitm-visibility.png` | MITM-mode forwarding setting and traffic counters | MITM position |
| `09-other-modes.png` | Takeover or flood results, if separately captured | Laboratory modes |

Before adding a screenshot, crop or redact unrelated external IPs, private payloads, credentials, session identifiers, and personal desktop details. Preserve the packet fields and timestamps needed to explain the observation. Do not create replacement terminal output or synthetic packet captures.
