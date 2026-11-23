"""Regression coverage for the HTTPS calls with modern target Python."""
import json
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from test_role import ROLE, load

prepare = load("prepare_https_test", "files/prepare.py")


class SecurityHealth(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        initialized = self.path == "/up"
        self.send_response(200 if initialized else 503)
        self.send_header("Content-Type", "application/json" if initialized else "text/plain")
        self.end_headers()
        self.wfile.write(b'{"status":"UP"}' if initialized else b"OpenSearch Security not initialized")


class HttpsTests(unittest.TestCase):
    def test_tls_and_bootstrap_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            ca = prepare.identity("test CA")
            cert = prepare.identity("indexer-test", ca, address="127.0.0.1")
            for name, value in [("ca", ca["cert"]), ("server", cert["cert"]), ("key", cert["key"]),
                                ("other", prepare.identity("different CA")["cert"])]:
                (directory / name).write_text(value)
            with HTTPServer(("127.0.0.1", 0), SecurityHealth) as server:
                tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                tls.load_cert_chain(directory / "server", directory / "key")
                server.socket = tls.wrap_socket(server.socket, server_side=True)
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    for path, authority, expected in [("/up", "ca", 200), ("/new", "ca", 503),
                                                      ("/up", "other", -1)]:
                        with self.subTest(path=path, ca=authority):
                            args = dict(url=f"https://127.0.0.1:{server.server_port}{path}",
                                        ca_path=str(directory / authority),
                                        status_code=[200, 503], return_content=True)
                            run = subprocess.run(
                                [sys.executable, str(ROLE / "library/wazuh_https.py")],
                                input=json.dumps({"ANSIBLE_MODULE_ARGS": args}), text=True,
                                capture_output=True,
                            )
                            result = json.loads(run.stdout)
                            self.assertEqual(result["status"], expected)
                            if expected == 200:
                                self.assertEqual(result["json"]["status"], "UP")
                            elif expected == 503:
                                self.assertIn("not initialized", result["content"])
                            else:
                                self.assertTrue(result["failed"])
                                self.assertIn("CERTIFICATE_VERIFY_FAILED", result["msg"])
                finally:
                    server.shutdown()
                    worker.join()
