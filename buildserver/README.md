# buildserver

Bereite einen Buildserver als solche vor, Stand Glupn v2022.1:

 * git (to get Gluon and other dependencies)
 * subversion
 * python3
 * build-essential
 * gawk
 * unzip
 * libncurses-dev (actually libncurses5-dev)
 * libz-dev (actually zlib1g-dev)
 * libssl-dev
 * wget
 * time (built-in time doesn’t work)
 * qemu-utils

Ziel ist es, eine Gluon-Build-Umgebung auf einem Debian-System schnell zu konfigurieren,
um danach per Build-Skript Gluon auf potenten, ggf. temporären, (Cloud-) Servern schnell
bauen zu können.