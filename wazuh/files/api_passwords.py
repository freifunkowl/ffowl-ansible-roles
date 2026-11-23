#!/usr/bin/python3
"""Verify the manager API accounts and initialize missing deployment passwords."""
import base64
import http.client
import json
import ssl
import sys
import syslog
import time

CAFILE = "/var/ossec/api/configuration/ssl/root-ca.pem"


def report(message):
    # Only fixed step names, known account names and numeric HTTP codes go here.
    print(message, flush=True)
    syslog.syslog(syslog.LOG_INFO, message)


class ApiFailure(Exception):
    def __init__(self, reason, transient=False):
        super().__init__(reason)
        self.transient = transient


def request(context, method, path, authorization, payload=None):
    connection = http.client.HTTPSConnection("127.0.0.1", 55000, context=context, timeout=65)
    headers = {"Authorization": authorization}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if response.status == 401 and method == "POST":
            return None
        if response.status != 200:
            raise ApiFailure("HTTP %d" % response.status, 500 <= response.status < 600)
        return response.read()
    finally:
        connection.close()


def token(context, name, password):
    basic = base64.b64encode((name + ":" + password).encode()).decode("ascii")
    body = request(context, "POST", "/security/user/authenticate?raw=true", "Basic " + basic)
    if body is None:
        return None
    value = body.decode("ascii").strip()
    if not value:
        raise ApiFailure("invalid response")
    return value


def api(context, path, bearer, payload=None):
    body = request(context, "PUT" if payload is not None else "GET",
                   path, "Bearer " + bearer, payload)
    result = json.loads(body)
    if result["error"] != 0 or result["data"].get("failed_items"):
        raise ApiFailure("API rejected request")
    return result["data"]


def initialize(context, passwords, updated):
    report("check wazuh")
    admin = token(context, "wazuh", passwords["wazuh"])
    change_admin = not admin
    if change_admin:
        report("check factory wazuh")
        admin = token(context, "wazuh", "wazuh")
        if not admin:
            raise ApiFailure("admin credentials rejected")
    report("check wazuh-wui")
    change_wui = not token(context, "wazuh-wui", passwords["wazuh-wui"])
    if not (change_admin or change_wui):
        return

    report("list accounts")
    users = api(context, "/security/users", admin)
    ids = {user["username"]: user["id"] for user in users["affected_items"]}
    for name, needed in (("wazuh-wui", change_wui), ("wazuh", change_admin)):
        if needed:
            report("update " + name)
            api(context, "/security/users/" + str(int(ids[name])), admin, {"password": passwords[name]})
            updated.add(name)

    for name in ("wazuh", "wazuh-wui"):
        report("verify " + name)
        if not token(context, name, passwords[name]):
            raise ApiFailure("verification failed")


def run():
    syslog.openlog("ffowl-wazuh-api")
    report("load configuration")
    try:
        passwords = json.load(sys.stdin)
        context = ssl.create_default_context(cafile=CAFILE)
        updated = set()
        for attempt in range(2):
            try:
                initialize(context, passwords, updated)
                print("changed" if updated else "ok", flush=True)
                return 0
            except ssl.SSLError:
                raise ApiFailure("TLS error")
            except (TimeoutError, OSError, http.client.HTTPException):
                failure = ApiFailure("connection error or timeout", True)
            except ApiFailure as exc:
                failure = exc
            if attempt or not failure.transient:
                raise failure
            report(str(failure))
            report("retry")
            time.sleep(5)
    except ApiFailure as exc:
        report(str(exc))
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        report("invalid configuration or response")
    return 1


if __name__ == "__main__":
    sys.exit(run())
