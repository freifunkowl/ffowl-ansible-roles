# bird

Diese Rolle installiert bird.

Im Normalfall (iBGP zwischen den Gateways, ggf. eBGP für Default-Route zum Upstream) gilt:

Bird setzt die Routen, um den Traffic durch die GRE-Tunnel zu leiten.
Das betrifft sowohl die GRE-Tunnel zwischen den Servern (siehe Rolle "backbone_gre_intern") als auch die GRE-Tunnel zu Freifunk Rheinland (siehe Rolle "gateways_gre_upstream").

Außerdem sendet Bird für IPv6 Router Advertisements in das Batman-Netz, wodurch Freifunk-Clients ihre IPv6-Adresse bekommen und erfahren, welche Router es gibt.

Ein Server kann aber auch als ›echter‹ BGP-Router für das eigene AS konfiguriert werden, hierzu ist in den host_vars »bgp_router: true« zu setzen, dann werden weitere Variablen ausgewertet:

- `router_id: 85.220.142.33`

  Setzt die Router-ID, Default: {{ipv4backbone16prefixstr}}255.{{vm_id}} (e. g. 192.168.255.4) — gilt unabhängig von »bgp_router: true« (denn 0.0.0.{{vm_id}} saugt).

- `loopback_ipv4: 85.220.142.33`

  Sourceadresse IPv4 für die gelernten Routen

- `loopback_ipv6: 2001:bf7:1352::1`

  Sourceadresse IPv6 für die gelernten Routen

- Ein eBGP-Peer kann wie folgt konfiguriert werden:

        ebgp_peers:
        - name: cix-ber1
          ipv4src: "185.1.74.52"
          ipv6src: "2001:7f8:a5::21:3106:2"
          ipv4dst: "185.1.74.1"
          ipv6dst: "2001:7f8:a5::5:7555:1"
          import4: "ANY"
          import6: "ANY"
          export4: "AS-FFLIP"
          export6: "AS213106"
          reimport_filter6: "AS213106"
          reimport_filter4: "AS213106"
          ouras:  213106
          peeras: 57555
          passwd: "PoohTheBear"
          exportlimit6: 50
          exportlimit4: 10

- Ähnlich sieht's bei iBGP aus:

        ibgp_peers:
        - name: fflip-fra01
          label:  "fra01"
          ipv4src: "185.1.74.52"
          ipv6src: "2001:7f8:a5::21:3106:2"
          ipv4dst: "185.1.74.51"
          ipv6dst: "2001:7f8:a5::21:3106:1"

- Und zu guter Letzt OSPF:

        ospf:
          interfaces:
          - name: Tfra01
            cost: 100
            options: "type broadcast;"

          - name: br-vms
            cost: 10
            options: "type broadcast;"

          stub_interfaces:
          - name: lo

          prefixes:
            ipv6:
              - 2001:bf7:1350::/44{44,64}
            ipv4:
              - 85.220.142.0/24{24,32}

# TODO:
Konfiguration erläutern:
- domaenenliste 
- more_specific_routes
- hostvars[host].hoster
- ffrl_nat_ip , ffnw_nat_ip
- ffrl_tun, ffnw_tun 
- ff_network.as_number
- ffrl/nw_tun.<tunnel>.bgp_local_pref