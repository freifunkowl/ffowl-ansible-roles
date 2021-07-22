# Ansible Smokeping Role

Fetched from https://github.com/overdrive3000/ansible-smokeping and adapted for FFOWL

## Ansible role to install and configure Smokeping

Example:

smokeping: true
smokeping_targets:
  - name: Public DNS
    target_group: DNS
    target_menu: DNS
    target_title: Public DNS
    target_hosts:
      - name: dns.google
        target_host_name: dns.google
        target_host_menu: dns.google
        target_host_title: Network Graph for dns.google
        target_host_host: dns.google
      - name: one.one.one.one
        target_host_name: one.one.one.one
        target_host_menu: one.one.one.one
        target_host_title: Network Graph for one.one.one.one
        target_host_host: one.one.one.one
      - name: dns9.quad9.net
        target_host_name: dns9.quad9.net
        target_host_menu: dns9.quad9.net
        target_host_title: Network Graph for dns9.quad9.net
        target_host_host: dns9.quad9.net
      - name: dns3.digitalcourage.de
        target_host_name: dns3.digitalcourage.de
        target_host_menu: dns3.digitalcourage.de
        target_host_title: Network Graph for dns3.digitalcourage.de
        target_host_host: dns3.digitalcourage.de
      - name: dns.as250.net
        target_host_name: dns.as250.net
        target_host_menu: dns.as250.net
        target_host_title: Network Graph for dns.as250.net
        target_host_host:  dns.as250.net
  - name: Peers
    target_group: Peers
    target_menu: Peers
    target_title: iBGP Peers
    target_hosts:
      - name: bgp-ber01
        target_host_name: bgp-ber01
        target_host_menu: bgp-ber01
        target_host_title: Network Graph for bgp-ber01.4830.org
        target_host_host: 193.26.120.86
      - name: bgp-dus01
        target_host_name: bgp-dus01
        target_host_menu: bgp-dus01
        target_host_title: Network Graph for bgp-dus01.4830.org
        target_host_host: 192.251.226.2
      - name: bgp-ber01
        target_host_name: bgp-fra01
        target_host_menu: bgp-fra01
        target_host_title: Network Graph for bgp-fra01.4830.org
        target_host_host: 193.26.120.81
      - name: bgp-ham02
        target_host_name: bgp-ham02
        target_host_menu: bgp-ham02
        target_host_title: Network Graph for bgp-ham02.4830.org
        target_host_host: 193.26.120.85
      - name: de2
        target_host_name: de2
        target_host_menu: de2
        target_host_title: Network Graph for de2.as206946.net
        target_host_host: 193.26.120.91
