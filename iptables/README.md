# iptables

Diese Rolle konfiguriert auf Gateways die IPv4-Netzwerkadressübersetzung (NAT bzw. SNAT)
in Verbinddung mit GRE-Tunneln (z. B. zum Freifunk Rheinland) sowie ggf. MSS-Einstellungen
wegen Tunneln mit MTU < 1500 Byte.

## Konfiguration

- `blocked_tcp_ports`: Liste von TCP-Ziel-Ports, die blockiert werden sollen (z. B. 25)
- `blocked_udp_ports`: Liste von UCP-Ziel-Ports, die blockiert werden sollen (z. B. 111)
