"""Regression tests for configuration edits, registration retries and key conflicts."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROLE = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROLE / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


config = load("config", "files/configure.py")
keys = load("keys", "library/wazuh_agent_key.py")
RECORD = "002 hv01 any " + "ab" * 32


class ConfigTests(unittest.TestCase):
    def test_agent_retains_existing_profile_and_extra_root(self):
        outside = "\n<ossec_config><localfile><location>/log/a&amp;b</location></localfile></ossec_config>\n"
        before = "<!-- <client>ignore</client> -->\n<ossec_config>\n"
        client = "<client><server><address>old</address></server><config-profile>custom</config-profile></client>"
        source = before + client + "\n</ossec_config>" + outside
        result = config.configure(source, "agent", "wazuh.example.net")
        self.assertTrue(result.startswith(before))
        self.assertTrue(result.endswith(outside))
        self.assertIn("<config-profile>custom</config-profile>", result)
        self.assertIn("<enabled>no</enabled>", result)
        self.assertIn("<address>wazuh.example.net</address>", result)
        self.assertEqual(result, config.configure(result, "agent", "wazuh.example.net"))
        with self.assertRaises(ValueError):
            config.configure(source.replace("</server>", "</server><server/>"), "agent", "host")

    def test_manager_retains_other_options(self):
        source = "<ossec_config><auth><disabled>yes</disabled><port>1515</port></auth></ossec_config>"
        result = config.configure(source, "server", None)
        self.assertIn("<disabled>no</disabled>", result)
        self.assertIn("<remote_enrollment>no</remote_enrollment>", result)
        self.assertIn("<port>1515</port>", result)
        self.assertEqual(result, config.configure(result, "server", None))


class KeyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.keys = Path(tmp.name, "client.keys")
        self.lock = Path(tmp.name, "lock")
        self.keys.write_text("001 other any otherkey\n 099 hv01 any void\n")
        self.module = SimpleNamespace(params={"name": "hv01", "existing_digest": ""},
                                      check_mode=False, run_command=Mock())

    def provision(self):
        return keys.provision(self.module, self.keys, self.lock)

    def test_registration_reuse_and_partial_retry(self):
        def add(args):
            self.assertEqual(args, ["/var/ossec/bin/manage_agents", "-a", "any", "-n", "hv01"])
            with self.keys.open("a") as fp:
                fp.write(RECORD + "\n")
            return 0, "", ""
        self.module.run_command.side_effect = add
        with patch.object(keys.os.path, "exists", return_value=True):
            self.assertEqual(self.provision(), (True, RECORD))
        self.assertEqual(self.provision(), (False, RECORD))  # retry before endpoint copy
        self.module.params["existing_digest"] = hashlib.sha256(RECORD.encode()).hexdigest()
        self.assertEqual(self.provision(), (False, RECORD))
        self.module.run_command.assert_called_once()

    def test_conflicts_and_check_mode(self):
        self.module.params["existing_digest"] = "existing-key-digest"
        with self.assertRaises(ValueError):
            self.provision()
        self.keys.write_text(RECORD + "\n")
        with self.assertRaises(ValueError):
            self.provision()
        self.module.params["existing_digest"] = ""
        self.keys.write_text(RECORD + "\n" + RECORD + "\n")
        with self.assertRaises(ValueError):
            self.provision()
        self.keys.write_text("")
        self.module.check_mode = True
        self.assertEqual(self.provision(), (True, ""))
        self.module.run_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
