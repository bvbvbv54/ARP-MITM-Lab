# 06 — My lab topology and VirtualBox

[Start](../README.md) · [Host discovery](02-host-discovery.md)

## The implemented lab topology

I ran the successful ARP poisoning experiment with a Parrot OS lab host, a Windows 11 victim, and a gateway in my controlled VirtualBox environment. The saved Parrot console and Windows neighbor screenshots show the `10.0.2.x` addresses below. The SVG artwork uses the documentation-only `192.0.2.x` range so the schematic stays reusable.

| Component | Captured lab IP | Network role |
| --- | --- | --- |
| Windows victim | `10.0.2.6` | Host whose gateway mapping changes |
| Parrot/Linux lab VM | `10.0.2.15` | Host implementing the ARP claims |
| Gateway | `10.0.2.1` | Genuine next hop for off-subnet traffic |

![Topology of normal local delivery](../assets/diagrams/normal-network.svg)

*ARP resolves the next-hop IPv4 address on the local link. It does not resolve an external server's MAC across a router.*

## Choosing an isolated VirtualBox link

An **Internal Network** with the same name on the relevant VMs keeps traffic among those VMs by default. It supplies no external gateway automatically: use an explicitly configured gateway VM if routed traffic is part of the lesson. A **Host-only** network lets the host participate with the VMs but ordinarily has no direct external LAN path; host services and host firewall behavior still matter. Ordinary per-VM **NAT** is not automatically a shared Layer 2 topology. **NAT Network** is a separate mode with guest-to-guest communication when configured on the same network. **Bridged** mode attaches to the physical LAN and can affect unrelated devices, so it is unsuitable for these demonstrations without a dedicated, authorized segment. See [Oracle's mode comparison](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/networkingdetails.html).

My successful poisoning test depended on the victim and lab host sharing a link on which the ARP claims could reach Windows. A new VirtualBox setup still needs its own route and shared-link checks; afterward, I verify cache recovery.

## What the screenshots show

The Windows gateway entry for `10.0.2.1` changed from the genuine gateway MAC to the Parrot OS lab MAC. Wireshark displayed ARP claims for the gateway and victim addresses. The Parrot console showed MITM mode with `forward=1` and increasing packet counters. The screenshots document the core poisoning result; they do not supply a separate takeover or flood result. See [testing notes](../results/README.md).
