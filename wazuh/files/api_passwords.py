#!/usr/bin/python3
"""Initialize the two factory API accounts using the local TLS listener."""
import base64
import json
import ssl
import sys
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

URL = "https://127.0.0.1:55000"
client = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context(
    cafile="/var/ossec/api/configuration/ssl/root-ca.pem")))


def token(user, password):
    basic = base64.b64encode((user + ":" + password).encode()).decode()
    req = Request(URL + "/security/user/authenticate?raw=true", method="POST",
                  headers={"Authorization": "Basic " + basic})
    try:
        with client.open(req, timeout=60) as response:
            return response.read().decode().strip()
    except HTTPError as exc:
        if exc.code == 401:
            return None
        raise


def api(path, bearer, data=None):
    req = Request(URL + path, data=json.dumps(data).encode() if data else None,
                  method="PUT" if data else "GET",
                  headers={"Authorization": "Bearer " + bearer, "Content-Type": "application/json"})
    with client.open(req, timeout=90) as response:
        result = json.load(response)
    if result.get("error") != 0 or result["data"].get("failed_items"):
        raise RuntimeError("Manager API declined account update")
    return result["data"]


def main():
    passwords = json.load(sys.stdin)
    admin = token("wazuh", passwords["wazuh"])
    if admin and token("wazuh-wui", passwords["wazuh-wui"]):
        print("ok")
        return
    new_admin = not admin
    admin = admin or token("wazuh", "wazuh")
    if not admin:
        raise SystemExit("API admin credentials do not match this deployment")
    ids = {u["username"]: u["id"] for u in api("/security/users", admin)["affected_items"]}
    for name in ("wazuh-wui", "wazuh"):
        if name == "wazuh" and not new_admin:
            continue
        api("/security/users/" + str(ids[name]), admin, {"password": passwords[name]})
    if not all(token(user, pwd) for user, pwd in passwords.items()):
        raise SystemExit("Updated API credentials failed verification")
    print("changed")


if __name__ == "__main__":
    main()
