#!/usr/bin/python3
"""Install one verified Certbot lineage and activate it for the selected service."""
import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import time

SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"


def install(lineage, directory, hostname, ca_file=SYSTEM_CA):
    # Certbot and Ansible take the same lock in main(). The published symlink
    # changes only after both files are ready and the whole chain is valid.
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        stage = Path(tmp)
        chain = stage / "fullchain.pem"
        key = stage / "privkey.pem"
        chain.write_bytes((lineage / chain.name).read_bytes())
        subprocess.run(["openssl", "pkcs8", "-topk8", "-nocrypt", "-in", lineage / key.name,
                        "-out", key], check=True)
        ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER).load_cert_chain(chain, key)
        subprocess.run(["openssl", "verify", "-purpose", "sslserver", "-verify_hostname", hostname,
                        "-CAfile", ca_file, "-untrusted", chain, chain], check=True,
                       stdout=subprocess.DEVNULL)
        leaf = chain.read_text().split("-----END CERTIFICATE-----", 1)[0] + "-----END CERTIFICATE-----"
        fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(leaf)).hexdigest()
        current = directory / "current"
        if current.is_symlink() and all((current / file.name).is_file() and (current / file.name).read_bytes() == file.read_bytes()
                                        for file in (key, chain)):
            return fingerprint, False
        previous = os.readlink(current) if current.is_symlink() else None
        gid = directory.stat().st_gid
        # A renewal may change the intermediate even when it reuses a leaf.
        # Publish a new, immutable directory for every changed pair.
        generation = Path(tempfile.mkdtemp(dir=directory, prefix="cert-"))
        try:
            os.chown(generation, -1, gid)
            generation.chmod(0o750)
            for file in (chain, key):
                os.chown(file, -1, gid)
                file.chmod(0o640)
                with file.open("rb") as stream:
                    os.fsync(stream.fileno())
                os.replace(file, generation / file.name)
            link = stage / "next"
            link.symlink_to(generation.name)
            os.replace(link, current)
        except BaseException:
            if not current.is_symlink() or os.readlink(current) != generation.name:
                shutil.rmtree(generation)
            raise
        # Retain the previous pair for readers completing an in-flight load.
        for old in directory.glob("cert-*"):
            if old.name not in (generation.name, previous) and old.is_dir() and not old.is_symlink():
                shutil.rmtree(old)
        return fingerprint, True


def wait_for_leaf(hostname, address, port, fingerprint, ca_file=SYSTEM_CA, timeout=90):
    context = ssl.create_default_context(cafile=ca_file)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((address, port), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as tls:
                    if hashlib.sha256(tls.getpeercert(binary_form=True)).hexdigest() == fingerprint:
                        return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError(f"{hostname}:{port} did not serve the renewed certificate")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=("indexer", "dashboard"))
    parser.add_argument("lineage", type=Path)
    parser.add_argument("hostname")
    parser.add_argument("address")
    parser.add_argument("--sync", action="store_true", help="Ansible activates the service after configuration")
    args = parser.parse_args()
    if not args.sync and os.environ.get("RENEWED_LINEAGE") != str(args.lineage):
        return
    os.umask(0o077)
    unit = "wazuh-" + args.component
    directory = Path("/etc") / unit / "certs/acme"
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fingerprint, changed = install(args.lineage, directory, args.hostname)
        if args.sync:
            print("changed" if changed else "ok")
            return
        if subprocess.run(["systemctl", "is-active", "--quiet", unit]).returncode != 0:
            return  # A stopped service reads this version on its next start.
        if args.component == "dashboard":
            subprocess.run(["systemctl", "try-restart", unit], check=True)
        port = 443 if args.component == "dashboard" else 9200
        wait_for_leaf(args.hostname, args.address, port, fingerprint, timeout=300 if port == 443 else 90)


if __name__ == "__main__":
    main()
