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
    (206813:400:0)             Route learned from transit (i. e. do not re-propagate)
    (206813:400:REMOTE_ASN)    Route learned from transit ASN

Traffic-Engineering:

    (206813:2:REMOTE_ASN)      Prepend 206813 to REMOTE_ASN
    (206813:2:0)               Prepend 206813 generally
    (206813:3:REMOTE_ASN)      Prepend 206813 2x to REMOTE_ASN
    (206813:3:0)               Prepend 206813 2x generally
    (206813:4:REMOTE_ASN)      Reject export to REMOTE_ASN
    (206813:4:0)               Reject export at all
    (206813:5:REMOTE_ASN)      Allow export to REMOTE_ASN (precedence over (206813:4:*))

    (206813:800:xxx)           Route originates at location xxx;
                               locations != xxx will prepend ASN twice
    (206813:801:xxx)           Route originates at location xxx;
                               locations != xxx will prepend ASN three times
    (206813:802:xxx)           Route originates at location xxx;
                               locations != xxx will prepend ASN four times

Locations (just use any consistent numbering, we use e. g.):

     1   DUS01 (PlusServer; formerly GUT01)
     2   BER01 (IN-BERLIN)
     3   FRA01 (vserver.site)
     4   HAM01 (irz42)
     5   HAM02 (IPHH)
     6   HAM03 (work)

IXPs (just use any consistent numbering >0, we use e. g.):

     1   Community-IX BER
     2   Community-IX FRA
     3   ECIX HAM
     4   DECIX HAM
     5   DECIX FRA (remote)
     6   DECIX DUS (local)
     7   DECIX DUS (remote)
     8   DECIX MUC (remote)
     9   BCIX
    10   DECIX FRA (local)
    11   LocIX
    12   KleyRex


## Configuration example ##

### bgp-ber01.4830.org ###

…/ffgt-ansible/host_vars/blackstar

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
      location: 1

    …
