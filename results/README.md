# Laboratory testing and results

[Start](../README.md) · [Victim observations](../docs/04-victim-observations.md)

I successfully ran the ARP poisoning experiment in my controlled Parrot OS / Windows 11 lab. My saved screenshots show the Windows gateway entry changing from the genuine gateway MAC (ending `…:01`) to my Parrot OS lab MAC (ending `…:24`). The Parrot console identifies the same lab MAC, shows `mode=mitm` with `forward=1`, and reports increasing packet counters. A Wireshark capture shows ARP claims for the gateway and victim IPs and duplicate-IP warnings.

| Check | Observation | Result |
| --- | --- | --- |
| Windows gateway mapping | `10.0.2.1` changed from the gateway MAC to the lab host MAC | **PASSED** |
| ARP packet visibility | Wireshark displayed the relevant ARP claims and duplicate-IP indications | **PASSED** |
| MITM-mode execution | Forwarding was enabled and the lab host reported nonzero packet counters | **PASSED** |

The original screenshots are in the [README gallery](../README.md#evidence-gallery). Exact performance values, application contents, and outcomes of the other two modes are not inferred from these images.

## Measurement worksheet

| Field | Baseline | During | Recovery |
| --- | --- | --- | --- |
| Local date and time | — | — | — |
| VirtualBox network mode and network name | — | — | — |
| Active victim interface and IPv4 | — | — | — |
| Default gateway IP and trusted MAC | — | — | — |
| Victim's observed gateway MAC | — | — | — |
| Gateway's observed victim MAC | — | — | — |
| ICMP replies / attempts | — | — | — |
| TCP target and successful connections / attempts | — | — | — |
| Capture reference and ARP frame interpretation | — | — | — |
| Connectivity from an unaffected control host | — | — | — |

For future numerical comparisons, record capture time, interface, and a short method description. Redact personal addresses, credentials, session data, payloads, and unrelated traffic before publication.
