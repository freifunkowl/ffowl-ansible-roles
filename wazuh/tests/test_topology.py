"""Exercise the shipped inventories, actual Jinja templates, PKI and manager edits."""
import ipaddress
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from xml.etree import ElementTree as ET

import bcrypt
import yaml
from ansible.errors import AnsibleFilterError
from ansible.plugins.filter.core import FilterModule
from cryptography import x509
from cryptography.x509.oid import NameOID
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from test_role import ROLE, config, load

layout = load("topology", "filter_plugins/topology.py").layout
templates = Environment(loader=FileSystemLoader(ROLE / "templates"), undefined=StrictUndefined)
templates.filters.update(FilterModule().filters())


def inventory(filename):
    data = json.loads(subprocess.check_output(
        ["ansible-inventory", "-i", str(ROLE / "examples" / filename), "--list"]))
    hosts = data["_meta"]["hostvars"]
    groups = {name: group.get("hosts", []) for name, group in data.items() if name != "_meta"}
    master = hosts[groups["wazuh_servers"][0]]["wazuh_master_host"]
    return layout(groups, hosts, master)


class DeploymentTests(unittest.TestCase):
    def render(self, template, **values):
        return yaml.safe_load(templates.get_template(template + ".j2").render(**values))

    def test_three_inventory_layouts(self):
        for name, expected in [("inventory.ini", (1, 1, 1, 1)),
                               ("distributed.ini", (1, 1, 1, 3)),
                               ("cluster.ini", (3, 2, 1, 6))]:
            with self.subTest(name=name):
                t = inventory(name)
                groups = [set(t[k]) for k in ("indexer", "manager", "dashboard")]
                self.assertEqual(tuple(map(len, groups)) + (len(set.union(*groups)),), expected)
                urls = [n["index_url"] for n in t["indexer"].values()]
                state = dict(initial_indexers=list(t["indexer"]), cluster_key="a" * 32,
                             passwords={"wazuh-wui": "test"})
                for kind in ("indexer", "manager", "dashboard"):
                    for node, details in t[kind].items():
                        values = dict(inventory_hostname=node, wazuh__node=details, wazuh__topo=t,
                                      wazuh__state=state, wazuh__index_urls=urls,
                                      wazuh_master_host=t["master"], wazuh_cluster_name="test")
                        if kind == "indexer":
                            conf = self.render("opensearch.yml", wazuh__bootstrap_discovery=True, **values)
                            self.assertEqual(conf["cluster.initial_master_nodes"], list(t[kind]))
                            self.assertEqual(conf["discovery.seed_hosts"], [h["endpoint"] for h in t[kind].values()])
                            self.assertEqual(conf["node.name"], node)
                            self.assertNotIn("cluster.initial_master_nodes", self.render(
                                "opensearch.yml", wazuh__bootstrap_discovery=False, **values))
                        elif kind == "manager":
                            settings = self.render("manager.json", **values)
                            sample = "<ossec_config><auth></auth><cluster></cluster><indexer></indexer></ossec_config>"
                            xml = config.configure(sample, "server", None, settings)
                            self.assertEqual(xml, config.configure(xml, "server", None, settings))
                            doc = ET.fromstring(xml)
                            self.assertEqual(doc.findtext("cluster/node_type"), "master" if node == t["master"] else "worker")
                            self.assertEqual(doc.findtext("cluster/disabled"), "yes" if len(t[kind]) == 1 else "no")
                            self.assertEqual(doc.findtext("cluster/nodes/node"), t[kind][t["master"]]["address"])
                            self.assertEqual([v.text for v in doc.findall("indexer/hosts/host")], urls)
                            self.assertEqual(self.render("filebeat.yml", **values)["output.elasticsearch"]["hosts"], urls)
                        else:
                            self.assertEqual(self.render("dashboard.yml", **values)["opensearch.hosts"], urls)
                            api = self.render("dashboard-api.yml", **values)["hosts"][0]["default"]
                            self.assertEqual(api["url"], "https://" + t["manager"][t["master"]]["endpoint"])

    def test_colocated_services_offer_distinct_trusted_identities(self):
        topo = inventory("inventory.ini")
        prepare = load("prepare", "files/prepare.py")
        state = prepare.provision(None, topo)
        host = topo["master"]
        address = topo["manager"][host]["address"]
        client = ssl.create_default_context(cadata=state["ca"]["cert"])

        def serve_once(listener, server):
            connection, _ = listener.accept()
            with server.wrap_socket(connection, server_side=True) as peer:
                peer.sendall(b"x")

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            jobs = []
            peers = []
            for kind in ("indexer", "manager", "dashboard"):
                self.assertEqual(topo[kind][host]["address"], address)
                pair = state["keys"][kind + "-" + host]
                pem = Path(directory, kind + ".pem")
                pem.write_text(pair["cert"] + pair["key"])
                server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                server.load_cert_chain(pem)
                listener = stack.enter_context(socket.socket())
                listener.bind(("127.0.0.1", 0))
                listener.listen()
                listener.settimeout(5)
                jobs.append((listener, server))

            with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
                futures = [pool.submit(serve_once, listener, server) for listener, server in jobs]
                for listener, _ in jobs:
                    with socket.create_connection(listener.getsockname(), timeout=5) as connection:
                        with client.wrap_socket(connection, server_hostname=address) as peer:
                            self.assertEqual(peer.recv(1), b"x")
                            cert = x509.load_der_x509_certificate(peer.getpeercert(binary_form=True))
                            peers.append(cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value)
                for future in futures:
                    future.result()
            self.assertEqual(peers, [kind + "-" + host for kind in ("indexer", "manager", "dashboard")])

    def test_credentials_reuse_and_certificate_scope(self):
        with tempfile.TemporaryDirectory() as td:
            topo = inventory("distributed.ini")
            node = next(iter(topo["indexer"]))
            def run():
                return subprocess.check_output([sys.executable, ROLE / "files/prepare.py", td],
                                               input=json.dumps(topo), text=True).strip()
            self.assertEqual(run(), "changed")
            path = Path(td) / "state.json"
            state = json.loads(path.read_text())
            ca = x509.load_pem_x509_certificate(state["ca"]["cert"].encode())
            for kind in ("indexer", "manager", "dashboard"):
                for host, details in topo[kind].items():
                    key = state["keys"][kind + "-" + host]
                    cert = x509.load_pem_x509_certificate(key["cert"].encode())
                    self.assertEqual(cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value, kind + "-" + host)
                    cert.verify_directly_issued_by(ca)
                    names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
                    self.assertIn(ipaddress.ip_address(details["address"]), names.get_values_for_type(x509.IPAddress))
                    self.assertTrue(key["key"].startswith("-----BEGIN PRIVATE KEY-----"))
            for user, hashed in state["hashes"].items():
                self.assertTrue(bcrypt.checkpw(state["passwords"][user].encode(), hashed.encode()))
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(run(), "ok")
            topo["indexer"][node]["address"] = "other.example"
            self.assertEqual(run(), "changed")
            updated = json.loads(path.read_text())
            for field in ["id", "ca", "admin", "passwords", "cluster_key", "initial_indexers"]:
                self.assertEqual(updated[field], state[field])
            self.assertNotEqual(updated["keys"]["indexer-" + node], state["keys"]["indexer-" + node])

    def test_invalid_assignment_and_ipv6(self):
        groups = {"wazuh_indexers": ["i"], "wazuh_servers": ["m"], "wazuh_dashboards": ["d"]}
        hosts = {name: {"ansible_host": "::1", "wazuh_node_address": "2001:db8::1"} for name in "imd"}
        self.assertEqual(layout(groups, hosts, "m")["indexer"]["i"]["index_url"], "https://[2001:db8::1]:9200")
        topo = layout(groups, hosts, "m")
        index_config = self.render("opensearch.yml", inventory_hostname="i", wazuh__node=topo["indexer"]["i"],
                                   wazuh__topo=topo, wazuh_cluster_name="test", wazuh__state={"initial_indexers":["i"]},
                                   wazuh__bootstrap_discovery=True)
        self.assertEqual(index_config["network.host"], "2001:db8::1")
        self.assertEqual(index_config["discovery.seed_hosts"], ["[2001:db8::1]"])
        long_name = "s" * 63
        long_layout = layout(dict(groups, wazuh_indexers=[long_name]),
                             dict(hosts, **{long_name: {"ansible_host": "10.0.0.10"}}), "m")
        self.assertLessEqual(len(long_layout["indexer"][long_name]["cn"]), 64)
        for changes, master in [({"wazuh_agents": ["m"]}, "m"), ({"wazuh_indexers": ["i", "d"]}, "m"),
                                ({"wazuh_indexers": []}, "m"), ({}, "d")]:
            with self.assertRaises(AnsibleFilterError):
                layout(dict(groups, **changes), hosts, master)


if __name__ == "__main__":
    unittest.main()
