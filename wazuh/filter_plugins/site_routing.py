"""Derive alert destinations from the same inventory that registers agents."""
import re

from ansible.errors import AnsibleFilterError


def alert_sites(groups, hostvars, local_site):
    nodes = {}
    agents = {}
    for host in groups.get("wazuh_indexers", []):
        site = str(hostvars[host].get("wazuh_rz", ""))
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,20}", site) or site == "unassigned":
            raise AnsibleFilterError(f"Set a valid wazuh_rz on indexer {host}")
        if site in nodes:
            raise AnsibleFilterError(f"Expected one indexer for {site}")
        nodes[site] = host
        for agent in groups.get("wazuh_rz_" + site, []):
            if agent in agents:
                raise AnsibleFilterError(f"{agent} belongs to more than one Wazuh site")
            agents[agent] = site
    if local_site not in nodes:
        raise AnsibleFilterError("wazuh_alert_local_rz must name an indexer site")
    # Filebeat uses the unassigned index for any agent absent from this map.
    nodes["unassigned"] = nodes[local_site]
    return {"nodes": nodes, "agents": agents}


class FilterModule:
    def filters(self):
        return {"ffowl_wazuh_alert_sites": alert_sites}
