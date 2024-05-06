#!/bin/sh -e
# {{ ansible_managed }}

(PATH=$PATH:/root/.local/bin ; export PATH ; cat /opt/icvpn-meta/{{ icvpn_communityname }} | shyaml  get-value networks.ipv6 | awk '{pfx[numpfx++]=$NF;} END{printf("LOCAL_ICVPN_PFX = [ "); if(numpfx>0) {for(i=0; i<numpfx; i++) {printf("%s%s", pfx[i], i<numpfx-1?", ":"");}} printf(" ];\n");}' >/etc/bird/bird6.conf.d/LOCAL_ICVPN_PFX_ ; mv /etc/bird/bird6.conf.d/LOCAL_ICVPN_PFX_ /etc/bird/bird6.conf.d/LOCAL_ICVPN_PFX)
(PATH=$PATH:/root/.local/bin ; export PATH ; cat /opt/icvpn-meta/{{ icvpn_communityname }} | shyaml  get-value networks.ipv4 | awk '{pfx[numpfx++]=$NF;} END{printf("LOCAL_ICVPN_PFX = [ "); if(numpfx>0) {for(i=0; i<numpfx; i++) {printf("%s%s", pfx[i], i<numpfx-1?", ":"");}} printf(" ];\n");}' >/etc/bird/bird.conf.d/LOCAL_ICVPN_PFX_ ; mv /etc/bird/bird.conf.d/LOCAL_ICVPN_PFX_ /etc/bird/bird.conf.d/LOCAL_ICVPN_PFX)

birdc configure > /dev/null ||:
birdc6 configure > /dev/null ||:
