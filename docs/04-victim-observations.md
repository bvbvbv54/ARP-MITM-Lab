# 04 — The Windows victim's view

[Start](../README.md) · [Results template](../results/README.md)

The author's successful ARP poisoning experiment used a Windows 11 victim. The published [`scripts/win11_probe.ps1`](../scripts/win11_probe.ps1) is the existing **read-only** observer. It reads the ARP cache and structured neighbor entries, samples reachability, and reports adapter statistics. It does not edit the cache or network configuration. Its default `GatewayIP` is `10.0.2.1`, a source-code default rather than a published measurement.

## Identify the active path

```powershell
ipconfig /all
route print
arp -a
```

`ipconfig /all` shows per-adapter addresses, masks, gateways, and MACs. `route print` shows the route table; find the default IPv4 route and its interface. `arp -a` shows cached IPv4 neighbors by interface. Select the adapter carrying the actual default route before comparing gateway entries. The script tries that route's adapter first, falling back to the first adapter marked Up; unusual multi-route setups warrant manual verification.

| Probe mode | Source behavior |
| --- | --- |
| `arp` | Raw `arp -a`, structured `Get-NetNeighbor`, then polls the gateway MAC every two seconds for `WatchSeconds` (default 30) |
| `baseline` | Cache, `Samples` ICMP echoes, and `Samples` TCP connection attempts to gateway port 443 |
| `during` | Baseline measurements plus a two-second adapter counter delta and established TCP peer summary |
| `counters` | Adapter counter delta and established TCP peer summary |

`Samples` defaults to 20. ICMP reports min/average/max response time for **replies received** and a loss percentage against requested probes. The TCP figure measures elapsed time until `ConnectAsync` completes or its wait returns, for successful completions included by the script; it is **not application throughput** and does not certify a completed TLS exchange. A gateway with no service on port 443 can make this metric unhelpful. Adapter packet and byte values are **two-second deltas for the selected adapter**, not counts attributable solely to the lab. Established-session grouping shows remote IPs, not captured payload. The summary reports time, mode, selected gateway, current gateway MAC, distinct MACs seen by the watch, adapter, and admin state.

## Compare states

Record a trusted baseline mapping, then a time-matched observation during an authorized isolated experiment, and finally a recovery state. If the gateway MAC changes, compare it with the actual gateway interface MAC and a packet capture of ARP replies. Verify whether connectivity changed and whether the router is still reachable from a separate unaffected host. Normal network reconfiguration, duplicate addressing, virtual adapter changes, and cache aging can also change entries. A changed mapping is an alert, **not conclusive proof of MITM**.

The script's own text sometimes calls multiple MACs “cache poisoning” or failed ping “gateway unreachable”; interpret those messages alongside the actual route and gateway state. The author confirms the core poisoning outcome, while the public repository contains no preserved victim-side terminal transcript. [Experiment record](../results/README.md) names the result and leaves numerical fields blank.
