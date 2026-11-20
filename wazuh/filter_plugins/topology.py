"""Resolve the deployment once from inventory aliases and service addresses."""
import hashlib
import ipaddress
import re

from ansible.errors import AnsibleFilterError


def layout(groups, hostvars, master, public_indexers=False):
    result = {}
    for kind, group in (("indexer", "wazuh_indexers"), ("manager", "wazuh_servers"), ("dashboard", "wazuh_dashboards")):
        nodes = {}
        for name in groups.get(group, []):
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}", name):
                raise AnsibleFilterError("Invalid inventory node name: " + name)
            host = hostvars[name]
            address = str(host.get("wazuh_node_address", host.get("ansible_host", name)))
            try:
                ip = ipaddress.ip_address(address)
                if ip.is_unspecified or ip.is_multicast:
                    raise AnsibleFilterError("Expected a reachable service address: " + address)
                endpoint = "[" + address + "]" if ip.version == 6 else address
            except ValueError:
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*", address):
                    raise AnsibleFilterError("Invalid DNS name: " + address)
                endpoint = address
            dns_name = str(host.get("wazuh_tls_dns_name", "")).lower()
            label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            if dns_name and (len(dns_name) > 253 or not re.fullmatch(rf"(?:{label}\.)+[a-z][a-z0-9-]*", dns_name)
                             or not all(re.fullmatch(label, part) for part in dns_name.split("."))):
                raise AnsibleFilterError("Invalid wazuh_tls_dns_name for " + name)
            if kind == "indexer" and public_indexers and not dns_name:
                raise AnsibleFilterError("Set wazuh_tls_dns_name on every public HTTPS indexer")
            http_host = dns_name if kind == "indexer" and public_indexers else endpoint
            common_name = kind + "-" + name
            if len(common_name) > 64:
                common_name = kind + "-" + hashlib.sha256(name.encode()).hexdigest()[:48]
            nodes[name] = dict(address=address, endpoint=endpoint,
                               dns_name=dns_name, index_url="https://" + http_host + ":9200", cn=common_name)
        if not nodes:
            raise AnsibleFilterError("Empty or missing inventory group: " + group)
        if len({n["address"] for n in nodes.values()}) != len(nodes):
            raise AnsibleFilterError("Each " + kind + " needs its own service address")
        result[kind] = nodes
    if master not in result["manager"]:
        raise AnsibleFilterError("Set wazuh_master_host to a member of wazuh_servers")
    if set(result["manager"]).intersection(groups.get("wazuh_agents", [])):
        raise AnsibleFilterError("Manager and agent packages conflict on the same host")
    result["master"] = master
    return result


class FilterModule:
    def filters(self):
        return {"ffowl_wazuh_layout": layout}
