# Laboratory screenshot gallery

[Back to project](../../README.md)

The [README gallery](../../README.md#evidence-gallery) embeds the four original screenshots from my completed lab, stored in [`screenshots/`](../../screenshots/). The diagrams elsewhere in the repository are illustrations, not substituted captures. This directory remains available for additional labeled images from later lab documentation.

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

For future screenshots, keep the fields and timestamps needed to explain the observation. Do not create replacement terminal output or synthetic packet captures.
