"""Regression tests for manager bootstrap, including interrupted updates."""
import base64
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from test_role import load

bootstrap = load("manager_api_passwords", "files/api_passwords.py")
PASSWORDS = {"wazuh": "local-admin-secret", "wazuh-wui": "local-ui-secret"}


class ManagerApiTests(unittest.TestCase):
    def setUp(self):
        self.accounts = {"wazuh": "wazuh", "wazuh-wui": "wazuh-wui"}
        self.writes = []
        self.failure = None

    def request(self, context, method, path, auth, payload=None):
        if self.failure:
            self.failure(method, path)
        if method == "POST":
            self.assertEqual(path, "/security/user/authenticate?raw=true")
            user, password = base64.b64decode(auth.removeprefix("Basic ")).decode().split(":", 1)
            return b"secret-token" if self.accounts[user] == password else None
        self.assertEqual(auth, "Bearer secret-token")
        ids = {"wazuh": 1, "wazuh-wui": 2}
        if method == "PUT":
            user = next(user for user, uid in ids.items() if path == "/security/users/" + str(uid))
            self.writes.append(user)
            self.accounts[user] = payload["password"]
        else:
            self.assertEqual((method, path), ("GET", "/security/users"))
        users = [{"username": name, "id": uid} for name, uid in ids.items()]
        return json.dumps({"error": 0, "data": {"affected_items": users}}).encode()

    def run_helper(self):
        with patch.object(bootstrap, "request", side_effect=self.request), \
                patch.object(bootstrap.ssl, "create_default_context"), \
                patch.object(bootstrap.time, "sleep"), \
                patch.object(bootstrap.sys, "stdin", io.StringIO(json.dumps(PASSWORDS))), \
                patch.object(bootstrap.syslog, "syslog"), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            rc = bootstrap.run()
        for value in [*PASSWORDS.values(), "secret-token"]:
            self.assertNotIn(value, output.getvalue())
        return rc, output.getvalue().splitlines()

    def test_initialization_and_idempotence(self):
        rc, lines = self.run_helper()
        self.assertEqual((rc, lines[-1]), (0, "changed"))
        self.assertEqual(self.writes, ["wazuh-wui", "wazuh"])
        self.assertEqual(self.run_helper(), (0, ["load configuration", "check wazuh", "check wazuh-wui", "ok"]))
        self.assertEqual(len(self.writes), 2)

    def test_resume_after_one_password_was_set(self):
        for changed, remaining in [("wazuh-wui", "wazuh"), ("wazuh", "wazuh-wui")]:
            with self.subTest(changed=changed):
                self.setUp()
                self.accounts[changed] = PASSWORDS[changed]
                self.assertEqual(self.run_helper()[0], 0)
                self.assertEqual(self.writes, [remaining])

    def test_transient_error_between_writes(self):
        def interrupt(method, path):
            if method == "PUT" and path.endswith("/1"):
                self.failure = None
                raise bootstrap.ApiFailure("HTTP 503", True)
        self.failure = interrupt
        rc, lines = self.run_helper()
        self.assertEqual((rc, lines[-1]), (0, "changed"))
        self.assertIn("retry", lines)
        self.assertEqual(self.writes, ["wazuh-wui", "wazuh"])

    def test_persistent_timeout_retries_once(self):
        def timeout(method, path):
            raise TimeoutError()
        self.failure = timeout
        rc, lines = self.run_helper()
        self.assertEqual(rc, 1)
        self.assertEqual(lines.count("retry"), 1)
        self.assertEqual(lines[-1], "connection error or timeout")
        self.assertFalse(self.writes)

    def test_credential_mismatch_stops(self):
        self.accounts["wazuh"] = "previous-deployment"
        rc, lines = self.run_helper()
        self.assertEqual((rc, lines[-1]), (1, "admin credentials rejected"))
        self.assertNotIn("retry", lines)
        self.assertFalse(self.writes)

    def test_rate_limit_stops(self):
        def reject(method, path):
            raise bootstrap.ApiFailure("HTTP 429")
        self.failure = reject
        rc, lines = self.run_helper()
        self.assertEqual((rc, lines[-1]), (1, "HTTP 429"))
        self.assertNotIn("retry", lines)
        self.assertFalse(self.writes)
