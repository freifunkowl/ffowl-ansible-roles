# bird configuration #

## tbd ##

### Communities ###

    (65535:65281)              NO_EXPORT
    (65535:65282)              NO_ADVERTISE
    (65535:666)                BLACKHOLE

### Large Communities ###

Read-only:

    (206813:0:REMOTE_ASN)      Route learned from REMOTE_ASN (legacy)
    (206813:1xx:REMOTE_ASN)    Route learned from REMOTE_ASN at IXP xx
    (206813:200:0)             Route learned from peer
    (206813:200:REMOTE_ASN)    Route learned from peer REMOTE_ASN
    (206813:300:0)             Route learned from "customer"
    (206813:300:REMOTE_ASN)    Route learned from "customer" ASN
    (206813:400:0)             Route learned from transit
    (206813:400:REMOTE_ASN)    Route learned from transit ASN
    (206813:500:xxx)           Route originates at location xxx (see below)

IXPs, 1xx, for xx use (just use any consistent numbering >0):

    01   Community-IX BER
    02   Community-IX FRA
    03   ECIX HAM
    04   DECIX HAM
    05   DECIX FRA (remote)
    06   DECIX DUS (local)
    07   DECIX DUS (remote)
    08   DECIX MUC (remote)
    09   BCIX
    10   DECIX FRA (local)
    11   LocIX
    12   KleyRex
    13   NL-ix BER

Traffic-Engineering:

    (206813:1:REMOTE_ASN)      Skip all prepends to REMOTE_ASN
    (206813:2:REMOTE_ASN)      Prepend 206813 to REMOTE_ASN
    (206813:2:0)               Prepend 206813 generally
    (206813:3:REMOTE_ASN)      Prepend 206813 2x to REMOTE_ASN
    (206813:3:0)               Prepend 206813 2x generally
    (206813:4:REMOTE_ASN)      Prepend 206813 3x to REMOTE_ASN
    (206813:4:0)               Prepend 206813 3x generally
    (206813:5:REMOTE_ASN)      Prepend 206813 4x to REMOTE_ASN
    (206813:5:0)               Prepend 206813 4x generally
    (206813:8:REMOTE_ASN)      Do not export to REMOTE_ASN
    (206813:8:0)               Do not export at all
    (206813:9:REMOTE_ASN)      Allow export to REMOTE_ASN (precedence over (206813:8:*))

    (206813:800:0) PLUS        Route originates at location xxx;
       (206813:800:xxx)        locations != xxx will prepend ASN once
    (206813:801:0) PLUS        Route originates at location xxx;
       (206813:801:xxx)        locations != xxx will prepend ASN twice times
     (206813:802:0) PLUS       Route originates at location xxx;
       (206813:802:xxx)        locations != xxx will prepend ASN three times
     (206813:803:0) PLUS       Route originates at location xxx;
       (206813:803:xxx)        locations != xxx will prepend ASN four times
     (206813:804:0) PLUS       Route originates at location xxx;
       (206813:804:xxx)        locations != xxx will prepend ASN five times

     (206813:899:0) PLUS       Route originates at location xxx;
       (206813:899:xxx)        locations != xxx will not export this prefix


Locations (just use any consistent numbering, we use e. g.):

     1   DUS01 (FFGT: PlusServer; formerly GUT01)
     2   BER01 (IN-BERLIN, Site AK)
     3   FRA01 (vserver.site (DC MK-Netzwerke))
     4   HAM01 (irz42; AS49745 location)
     5   HAM02 (IPHH)
     6   HAM03 (n@work)
     7   AMS01 (coloclue (DC EuNetworks); AS49745 location)
     8   HEL01 (Hetzner HEL, AS49745 location)
     9   FKS01 (Hetzner FKS, AS49745 location)
    10   ATL01 (Vultr ATL, AS206946 location)
    11   SIN01 (Vultr SIN, AS206946 location)
    12   FRA02 (DECIX-Colo in Interxion FRA1)
    13   FRA03 (meerbarbig-Colo)

## Configuration example ##

### bgp-ber01.4830.org ###

…/ffgt-ansible/host_vars/blackstar

[…]
    location: 1

    ebgp_peers:
    …
    - name: "AS213106_1"
      ipv4src: "185.1.74.16"
      ipv6src: "2001:7f8:a5::20:6813:1"
      ipv4dst: "185.1.74.51"
      ipv6dst: "2001:7f8:a5::21:3106:1"
      peeras:  "213106"
      import6: "AS-FFLIP"
      import4: "AS-FFLIP"
      export6: "AS-FFGT"
      export4: "AS-FFGT"
      export_filter4: "fix_exp.inc"
      import_filter4: "fix_imp.inc"
      export_filter6: "fix_exp.inc"
      import_filter6: "fix_imp.inc"
      reimport_filter6: "AS206813"
      reimport_filter4: "AS206813"
      exportlimit6: 50
      exportlimit4: 10
      community_in: 200

[…]
