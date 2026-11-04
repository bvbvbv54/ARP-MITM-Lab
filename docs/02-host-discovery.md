# 02 — Why discovery commands disagree

[Start](../README.md) · [Topology](06-network-topology.md)

Different commands inspect different parts of a network. A short list from one tool is not proof that the other devices disappeared.

| Tool | What it reveals | What it does not reveal |
| --- | --- | --- |
| `ip addr` / `ip -br addr` | IPs configured on this Linux host | Other machines |
| `ip route` | This host's route choices | Which hosts are alive |
| `ip neigh` | Entries this host has learned or configured on local links | A complete subnet inventory |
| Windows `arp -a` | This Windows host's ARP cache | All reachable systems |
| `ping` | Whether an ICMP echo response arrives now | Whether a silent host is offline |
| Nmap host discovery | Which scoped targets respond to its selected probes | Every host or every open port |
| Nmap port scan | Responses from selected transport ports on scoped targets | A guarantee that all ports or services were found |

## Local configuration versus learned neighbors

`ip addr` reports interfaces on **the machine running it**. `ip route` decides which interface and next hop an IP packet should use. `ip neigh` reports neighbor entries acquired through local traffic or configuration. Entries can be stale, and an untouched host may be absent. Windows `arp -a` has the same cache-versus-inventory limitation.

An ICMP echo reply shows that a reply reached the sender. A failed ping can reflect a firewall, filtered ICMP, routing failure, host sleep, or timing. It is not a definitive offline verdict.

## Bounded active discovery

Nmap host discovery asks targets in an explicitly authorized scope to respond. Its exact probes depend on target location, privileges, options, and version; on local Ethernet it may use ARP. Host discovery is distinct from examining open TCP or UDP ports. For an **owned, isolated lab subnet only**, the illustrative form is:

```bash
nmap -sn <authorized-lab-subnet>
```

`-sn` requests host discovery without a port scan. A response identifies a system that answered the chosen probes; nonresponse is inconclusive. See the [Nmap host-discovery reference](https://nmap.org/book/man-host-discovery.html).

## VirtualBox changes what “local” means

| Mode | Relevant link behavior | Lab implication |
| --- | --- | --- |
| Ordinary NAT | Each VM is generally behind its own NAT engine; default peer-to-peer VM access is absent | Do **not** assume two NAT guests share one ARP domain |
| NAT Network | VMs attached to the same configured NAT Network can communicate | Check the actual shared segment and routing |
| Bridged | Guest connects to the physical LAN through the host adapter | Can expose the experiment to other LAN devices; unsuitable for casual isolation |
| Host-only | VMs and host share a private virtual network, without ordinary external LAN access | Useful for controlled observations; the host also participates |
| Internal Network | VMs on the same named virtual network share a private segment, without host or outside connectivity by default | Strong isolation; add a gateway VM if the lesson needs routing |

Two machines having IPv4 addresses does **not** prove they share a reachable Layer 2 segment. Ordinary ARP claims remain on their local link and do not ordinarily cross routers. Use the [VirtualBox networking guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/networkingdetails.html) for mode details.

## A practical reading of differing results

If `ip neigh` shows one entry and Nmap reports several hosts, the cache may contain only recent neighbors while Nmap actively probed a broader scope. If Nmap sees fewer hosts, check the selected interface, subnet boundary, permissions, firewall and ICMP behavior, probe selection, and timing. An old cache entry can survive after a host leaves. These differences explain why the commands I used during network investigation answer different questions; the saved screenshots document the ARP experiment rather than a paired Nmap scan.
