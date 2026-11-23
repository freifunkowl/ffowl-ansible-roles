#!/usr/bin/python
"""Call the local Wazuh APIs over verified HTTPS on the managed host."""
import base64
import http.client
import json
import ssl
from urllib.parse import urlsplit

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type="str", required=True),
            ca_path=dict(type="path", required=True),
            method=dict(choices=["GET", "POST", "PUT"], default="GET"),
            url_username=dict(type="str"),
            url_password=dict(type="str", no_log=True),
            body=dict(type="dict"),
            status_code=dict(type="list", elements="int", default=[200]),
            return_content=dict(type="bool", default=False),
        ),
        required_together=[("url_username", "url_password")],
    )
    args = module.params
    connection = None
    try:
        url = urlsplit(args["url"])
        if url.scheme != "https" or not url.hostname or url.username is not None or url.fragment:
            module.fail_json(msg="Expected an absolute HTTPS URL without credentials or fragment", status=-1)
        context = ssl.create_default_context(cafile=args["ca_path"])
        connection = http.client.HTTPSConnection(url.hostname, port=url.port, context=context, timeout=30)
        headers = {"Accept": "application/json"}
        if args["url_username"] is not None:
            credentials = (args["url_username"] + ":" + args["url_password"]).encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(credentials).decode("ascii")
        body = None
        if args["body"] is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(args["body"]).encode("utf-8")
        path = url.path or "/"
        if url.query:
            path += "?" + url.query
        connection.request(args["method"], path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read().decode("utf-8", errors="replace")
        result = {"status": response.status, "changed": False}
        if args["return_content"]:
            result["content"] = content
        if response.status not in args["status_code"]:
            module.fail_json(msg="Unexpected HTTP status %d" % response.status, **result)
        if content and response.headers.get_content_subtype().lower().split("+")[-1] == "json":
            try:
                result["json"] = json.loads(content)
            except ValueError:
                # The security plugin can return a plain-text bootstrap response.
                pass
    except (OSError, ValueError, http.client.HTTPException) as exc:
        module.fail_json(msg=str(exc), status=-1)
    finally:
        if connection is not None:
            connection.close()
    module.exit_json(**result)


if __name__ == "__main__":
    main()
