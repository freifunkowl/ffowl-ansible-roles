"""Public HTTP identities stay independent of cluster membership and client trust."""
import copy
import ipaddress
import unittest

from ansible.errors import AnsibleFilterError
from cryptography import x509

from test_role import load
import test_topology
from test_topology import layout

prepare = load("prepare_acme", "files/prepare.py")


class PublicTlsTests(unittest.TestCase):
    def setUp(self):
        self.groups = {"wazuh_indexers": ["i"], "wazuh_servers": ["m"], "wazuh_dashboards": ["m"]}
        self.hosts = {"i": {"ansible_host": "192.0.2.1", "wazuh_tls_dns_name": "index.example.net"},
                      "m": {"ansible_host": "192.0.2.2", "wazuh_tls_dns_name": "ui.example.net"}}

    def test_dns_and_trust_on_both_https_listeners(self):
        render = test_topology.DeploymentTests().render
        for public in (False, True):
            with self.subTest(public=public):
                t = layout(self.groups, self.hosts, "m", public)
                idx = t["indexer"]["i"]
                self.assertEqual(idx["index_url"], "https://" + ("index.example.net" if public else "192.0.2.1") + ":9200")
                conf = render("opensearch.yml", wazuh__topo=t, wazuh_cluster_name="test", inventory_hostname="i",
                              wazuh__node=idx, wazuh__bootstrap_discovery=True, wazuh__state={"initial_indexers": ["i"]}, wazuh_indexer_letsencrypt=public)
                self.assertEqual(conf["network.host"], "192.0.2.1")
                self.assertEqual(conf["plugins.security.ssl.http.pemtrustedcas_filepath"], "/etc/wazuh-indexer/certs/root-ca.pem")
                self.assertEqual(conf["plugins.security.ssl.transport.pemcert_filepath"], "/etc/wazuh-indexer/certs/indexer.pem")
                self.assertNotIn("plugins.security.ssl.transport.enforce_cert_reload_dn_verification", conf)
                self.assertEqual("acme/" in conf["plugins.security.ssl.http.pemcert_filepath"], public)
                dash = render("dashboard.yml", wazuh__node=t["dashboard"]["m"], wazuh__index_urls=[idx["index_url"]],
                              wazuh_dashboard_letsencrypt=True, wazuh_indexer_letsencrypt=public)
                self.assertEqual(dash["server.ssl.certificate"], "/etc/wazuh-dashboard/certs/acme/current/fullchain.pem")
                self.assertEqual(dash["opensearch.ssl.certificateAuthorities"][0],
                                 "/etc/ssl/certs/ca-certificates.crt" if public else "/etc/wazuh-dashboard/certs/root-ca.pem")

    def test_fqdn_added_to_previous_state(self):
        old = {host: {"ansible_host": v["ansible_host"]} for host, v in self.hosts.items()}
        prior = prepare.provision(None, layout(self.groups, old, "m"))
        for key in prior["keys"].values():
            key.pop("dns_name")  # installations created before DNS SANs
        t = layout(self.groups, self.hosts, "m")
        newer = prepare.provision(copy.deepcopy(prior), t)
        for key in ("ca", "admin", "id", "passwords", "cluster_key"):
            self.assertEqual(prior[key], newer[key])
        self.assertNotEqual(prior["keys"]["indexer-i"], newer["keys"]["indexer-i"])
        cert = x509.load_pem_x509_certificate(newer["keys"]["indexer-i"]["cert"].encode())
        names = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        self.assertIn("index.example.net", names.get_values_for_type(x509.DNSName))
        self.assertIn(ipaddress.ip_address("192.0.2.1"), names.get_values_for_type(x509.IPAddress))
        self.assertEqual(newer, prepare.provision(copy.deepcopy(newer), t))

    def test_public_indexers_require_fqdn(self):
        for bad in ("", "shortname", "*.example.net", "192.0.2.1", "-broken.example.net"):
            self.hosts["i"]["wazuh_tls_dns_name"] = bad
            with self.subTest(bad=bad), self.assertRaises(AnsibleFilterError):
                layout(self.groups, self.hosts, "m", True)
