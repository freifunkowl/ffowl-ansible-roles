"""Verify site assignment independently of the SSH address or gateway name."""
import unittest

from ansible.errors import AnsibleFilterError
from test_role import load

sites = load("site_routing", "filter_plugins/site_routing.py").alert_sites


class SiteRoutingTests(unittest.TestCase):
    def setUp(self):
        self.groups = {"wazuh_indexers": ["i1", "i2"], "wazuh_agents": ["ep1"],
                       "wazuh_rz_ham": ["ep1", "spare"], "wazuh_rz_ber": []}
        self.hosts = {"i1": {"wazuh_rz": "ham"}, "i2": {"wazuh_rz": "ber"}}

    def test_inventory_alias_and_reserved_fallback(self):
        result = sites(self.groups, self.hosts, "ham")
        self.assertEqual(result["agents"], {"ep1": "ham", "spare": "ham"})
        self.assertEqual(result["nodes"], {"ham": "i1", "ber": "i2", "unassigned": "i1"})

    def test_ambiguous_or_missing_site(self):
        for changes in ({"wazuh_rz_ber": ["ep1"]}, {"wazuh_agents": ["absent"]}):
            with self.subTest(changes=changes), self.assertRaises(AnsibleFilterError):
                sites(dict(self.groups, **changes), self.hosts, "ham")
        for value in ("ham", "unassigned", ""):
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                sites(self.groups, dict(self.hosts, i2={"wazuh_rz": value}), "ham")
        with self.assertRaises(AnsibleFilterError):
            sites(self.groups, self.hosts, "fra")
