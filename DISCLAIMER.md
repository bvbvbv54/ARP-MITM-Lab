# Responsible laboratory use

This project is for controlled education on systems and networks you own or have explicit permission to assess. ARP manipulation can redirect or interrupt connectivity for devices sharing a local link. Do not use the scripts on public, university, employer, or third-party networks without explicit authorization. Do not collect credentials, session data, or private traffic belonging to others. Follow applicable law and institutional rules; an educational label does not grant permission.

Use a dedicated VirtualBox Internal Network for VM-only isolation, with a separately configured gateway VM if routing is needed. Host-only networking can also isolate from the physical LAN, but the host participates and must be considered in the scope. Ordinary per-VM NAT is not automatically a shared Layer 2 segment. Avoid bridged attachment to a shared LAN for these demonstrations. Confirm the topology and a recovery path before experiments; verify legitimate neighbor mappings and connectivity afterward.

The documentation distinguishes source-code behavior from measured outcomes. No experimental results are asserted without saved evidence.
