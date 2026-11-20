#!/usr/bin/python
"""Ansible module delegated to the manager. Return only the requesting host's key."""
import fcntl
import hashlib
from contextlib import nullcontext
import os
import re
import time

from ansible.module_utils.basic import AnsibleModule


def find_key(keys_file, name):
    with open(keys_file, encoding="utf-8") as src:
        records = []
        for line in src:
            if not line or line[0].isspace() or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) == 4 and fields[1] == name:
                if not re.fullmatch(r"[0-9]{3,8}", fields[0]) or int(fields[0]) == 0:
                    raise ValueError("Invalid agent ID in manager client.keys")
                records.append(line.rstrip("\r\n"))
    if len(records) > 1:
        raise ValueError("Multiple manager records have the same agent name")
    return records[0] if records else None


def provision(module, keys_file="/var/ossec/etc/client.keys",
              lock_file="/run/ffowl-wazuh-agent-keys.lock"):
    name = module.params["name"]
    previous = module.params["existing_digest"]
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}", name):
        raise ValueError("Invalid Wazuh agent name")
    # Serialize read/add across Ansible forks and independent playbook runs.
    # Wazuh itself owns and updates client.keys through the local authd socket.
    with (nullcontext() if module.check_mode else open(lock_file, "a")) as lock:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_EX)
        key = find_key(keys_file, name)
        if key:
            if previous and hashlib.sha256(key.encode()).hexdigest() != previous:
                raise ValueError("The endpoint and manager already have different keys")
            return False, key
        if previous:
            raise ValueError("The endpoint already has a key, but the manager has no matching name")
        if module.check_mode:
            return True, ""
        if not os.path.exists("/var/ossec/queue/sockets/auth"):
            raise ValueError("The manager's local authd socket is missing")
        rc, _, _ = module.run_command(["/var/ossec/bin/manage_agents", "-a", "any", "-n", name])
        # authd persists new records asynchronously. Re-read even after an
        # error, since an external administrator may have added the same name.
        for unused in range(40):
            key = find_key(keys_file, name)
            if key:
                return rc == 0, key
            time.sleep(0.25)
        raise ValueError("manage_agents did not register this name (exit %d). See manager ossec.log" % rc)


def main():
    module = AnsibleModule(argument_spec=dict(name=dict(type="str", required=True),
                                               existing_digest=dict(type="str", default="")),
                           supports_check_mode=True)
    try:
        changed, key = provision(module)
    except (OSError, ValueError) as error:
        module.fail_json(msg=str(error))
    module.exit_json(changed=changed, key=key)


if __name__ == "__main__":
    main()
