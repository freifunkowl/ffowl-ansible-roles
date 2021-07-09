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
    (206813:300:REMOTE_ASN)    Route learned from "customer" ASN
    (206813:400:0)             Route learned from transit
    (206813:400:REMOTE_ASN)    Route learned from transit ASN

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

Traffic-Engineering:

    (206813:2:REMOTE_ASN)      Prepend 206813 to REMOTE_ASN
    (206813:2:0)               Prepend 206813 generally
    (206813:3:REMOTE_ASN)      Prepend 206813 2x to REMOTE_ASN
    (206813:3:0)               Prepend 206813 2x generally
    (206813:4:REMOTE_ASN)      Reject export to REMOTE_ASN
    (206813:4:0)               Reject export at all
    (206813:5:REMOTE_ASN)      Allow export to REMOTE_ASN (precedence over (206813:4:*))

    (206813:800:0) PLUS        Route originates at location xxx;
       (206813:800:xxx)        locations != xxx will prepend ASN once
    (206813:801:0) PLUS        Route originates at location xxx;
       (206813:801:xxx)        locations != xxx will prepend ASN twice times
     (206813:802:0) PLUS        Route originates at location xxx;
       (206813:802:xxx)        locations != xxx will prepend ASN three times

Locations (just use any consistent numbering, we use e. g.):

     1   DUS01 (FFGT: PlusServer; formerly GUT01; FFLIP: vserver.site DUS1)
     2   BER01 (IN-BERLIN, Site AK)
     3   FRA01 (vserver.site (DC MK-Netzwerke))
     4   HAM01 (irz42; AS49745 location)
     5   HAM02 (IPHH)
     6   HAM03 (n@work)
     7   AMS01 (coloclue (DC EuNetworks); AS49745 location)



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