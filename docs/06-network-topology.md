# 06 — Topology and evidence boundaries

[Start](../README.md) · [Host discovery](02-host-discovery.md)

## The implemented lab topology

The author's successful ARP poisoning run involved a Parrot/Linux lab host, a Windows 11 victim, and a gateway in a controlled VirtualBox environment. The source's `10.0.2.x` addresses are defaults and examples, not published measurements of that run. All artwork uses **illustrative addresses**.

| Component | Example label | Network role |
| --- | --- | --- |
| Windows victim | `10.0.2.6` | Host whose gateway mapping changes |
| Parrot/Linux lab VM | `10.0.2.15` | Host implementing the ARP claims |
| Gateway | `10.0.2.1` | Genuine next hop for off-subnet traffic |

![Topology of normal local delivery](../assets/diagrams/normal-network.svg)

*ARP resolves the next-hop IPv4 address on the local link. It does not resolve an external server's MAC across a router.*

## Choosing an isolated VirtualBox link

An **Internal Network** with the same name on the relevant VMs keeps traffic among those VMs by default. It supplies no external gateway automatically: use an explicitly configured gateway VM if routed traffic is part of the lesson. A **Host-only** network lets the host participate with the VMs but ordinarily has no direct external LAN path; host services and host firewall behavior still matter. Ordinary per-VM **NAT** is not automatically a shared Layer 2 topology. **NAT Network** is a separate mode with guest-to-guest communication when configured on the same network. **Bridged** mode attaches to the physical LAN and can affect unrelated devices, so it is unsuitable for these demonstrations without a dedicated, authorized segment. See [Oracle's mode comparison](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/networkingdetails.html).

The successful ARP poisoning result confirms the author ran a working lab arrangement. Reproducing it requires checking routes and shared-link membership in the new environment; afterward, verify cache recovery.

## Claims ledger

| Claim | Status in this repository |
| --- | --- |
| ARP poisoning succeeded in the controlled lab | Confirmed by the project author |
| Local Python script defines three modes and attempts normal teardown restoration | Verified by source inspection; source is not in the public checkout |
| Published Windows script observes cache, reachability, and counters without changing configuration | Verified by source inspection; available in `scripts/win11_probe.ps1` |
| Traffic was transparently relayed or connectivity failed during a specific run | No published measurement supporting a mode-specific claim |
| A flood overflowed a table or caused a measured outage | No published capture or measurement |
| The example `10.0.2.x` addresses were actually used in VirtualBox | Examples only |
