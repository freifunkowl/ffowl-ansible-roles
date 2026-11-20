#!/usr/bin/env python3
"""Create/reuse a private deployment manifest on the Ansible controller."""
import argparse
import datetime
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

import bcrypt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def identity(cn, issuer=None, address=None, dns_name=""):
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Wazuh"),
                      x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.datetime.now(datetime.timezone.utc)
    signer = serialization.load_pem_private_key(issuer["key"].encode(), None) if issuer else key
    subject = x509.load_pem_x509_certificate(issuer["cert"].encode()).subject if issuer else name
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1825 if issuer else 3650))
            .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=None if issuer else 0), True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(signer.public_key()), False)
            .add_extension(x509.KeyUsage(True, False, bool(issuer), False, False, not issuer, not issuer, False, False), True))
    if issuer:
        cert = cert.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]), False)
    if address:
        names = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(address)))
        except ValueError:
            names.append(x509.DNSName(address))
        if dns_name:
            names.append(x509.DNSName(dns_name))
        cert = cert.add_extension(x509.SubjectAlternativeName(list(dict.fromkeys(names))), False)
    return dict(key=key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                      serialization.NoEncryption()).decode(),
                cert=cert.sign(signer, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode())


def provision(state, topo):
    if state is None:
        ca = identity("FFOWL Wazuh CA")
        # Fixed character classes meet the Wazuh API password policy.
        passwords = {n: secrets.token_hex(20) + "aA9*" for n in ("admin", "kibanaserver", "wazuh", "wazuh-wui")}
        state = dict(ca=ca, admin=identity("admin", ca), passwords=passwords, keys={},
                     cluster_key=secrets.token_hex(16), id=secrets.token_hex(16),
                     initial_indexers=list(topo["indexer"]), hashes={n: bcrypt.hashpw(
                         passwords[n].encode(), bcrypt.gensalt(prefix=b"2a")).decode() for n in ("admin", "kibanaserver")})
    for kind in ("indexer", "manager", "dashboard"):
        for name, node in topo[kind].items():
            ident = kind + "-" + name
            old = state["keys"].get(ident)
            dns_name = node.get("dns_name", "")
            if not old or old["address"] != node["address"] or old.get("dns_name", "") != dns_name:
                state["keys"][ident] = dict(address=node["address"], dns_name=dns_name,
                                            **identity(node["cn"], state["ca"], node["address"], dns_name))
    return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    topo = json.load(sys.stdin)
    os.umask(0o077)
    directory = args.directory
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise SystemExit("State directory must be private (chmod 700)")
    path = directory / "state.json"
    with (directory / "state.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original = path.read_text() if path.exists() else ""
        state = provision(json.loads(original) if original else None, topo)
        data = json.dumps(state, sort_keys=True, indent=2) + "\n"
        if data == original:
            print("ok")
            return
        with tempfile.NamedTemporaryFile("w", dir=directory, delete=False) as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(out.name, path)
        print("changed")


if __name__ == "__main__":
    main()
