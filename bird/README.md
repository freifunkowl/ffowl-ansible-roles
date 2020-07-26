# bird

Diese Rolle installiert bird.

Im Normalfall (iBGP unter den Gateways, ggf. eBGP für Default-Route zum Upstream) gilt:

Bird setzt die Routen, um den Traffic durch die GRE-Tunnel zu leiten.
Das betrifft sowohl die GRE-Tunnel zwischen den Servern (siehe Rolle "backbone_gre_intern") als auch die GRE-Tunnel zu Freifunk Rheinland (siehe Rolle "gateways_gre_upstream").

Außerdem sendet Bird für IPv6 Router Advertisements in das Batman-Netz, wodurch Freifunk-Clients ihre IPv6-Adresse bekommen und erfahren, welche Router es gibt.

Ein Server kann aber auch als ›echter‹ BGP-Router für das eigene AS konfiguriert werden, hierzu ist in den host_vars »bgp_router: true« zu setzen, dann werden weitere Variablen ausgewertet:

- router_id: 85.220.142.33

  Setzt die Router-ID, Default: {{ipv4backbone16prefixstr}}255.{{vm_id}} (e. g. 192.168.255.4)

- loopback_ipv4: 85.220.142.33

  Sourceadresse für die gelernten Routen

- loopback_ipv6: 2001:bf7:1352::1

  Sourceadresse für die gelernten Routen



# TODO:
Konfiguration erläutern:
- domaenenliste 
- more_specific_routes
- hostvars[host].hoster
- ffrl_nat_ip , ffnw_nat_ip
- ffrl_tun, ffnw_tun 
- ff_network.as_number
- ffrl/nw_tun.<tunnel>.bgp_local_pref