#!/usr/bin/python3
"""Update agent transport or the manager's enrollment, cluster and indexer settings."""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.dom import Node, minidom
from xml.parsers.expat import ExpatError


def ensure_element(parent, name, indent):
    children = [n for n in parent.childNodes if n.nodeType == Node.ELEMENT_NODE and n.tagName == name]
    if len(children) > 1:
        raise ValueError("Ambiguous <%s> in <%s>. Check the single-manager configuration." % (name, parent.tagName))
    if children:
        return children[0]
    doc = parent.ownerDocument
    child = doc.createElement(name)
    tail = parent.lastChild
    if tail and tail.nodeType == Node.TEXT_NODE and not tail.data.strip():
        parent.removeChild(tail)
    parent.appendChild(doc.createTextNode("\n" + " " * indent))
    parent.appendChild(child)
    parent.appendChild(doc.createTextNode("\n" + " " * (indent - 2)))
    return child


def set_value(parent, name, value, indent=4):
    node = ensure_element(parent, name, indent)
    old_value = "".join(n.data for n in node.childNodes if n.nodeType == Node.TEXT_NODE)
    if old_value.strip() != value:
        if any(n.nodeType == Node.ELEMENT_NODE for n in node.childNodes):
            raise ValueError("Unexpected child element in <%s>" % name)
        for n in list(node.childNodes):
            if n.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
                node.removeChild(n)
        node.appendChild(node.ownerDocument.createTextNode(value))


def edit_section(source, tag, update):
    tokens = re.finditer(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|</?" + tag + r"\s*>", source, re.S)
    bounds = [m for m in tokens if not m.group().startswith("<!")]
    if len(bounds) != 2 or bounds[0].group().startswith("</") or not bounds[1].group().startswith("</"):
        raise ValueError("Expected exactly one active <%s> section" % tag)
    start, end = bounds[0].start(), bounds[1].end()
    node = minidom.parseString(source[start:end]).documentElement
    before = node.toxml()
    update(node)
    after = node.toxml()
    return source if after == before else source[:start] + after + source[end:]


def set_list(parent, name, item, values):
    target = ensure_element(parent, name, 4)
    old = [n for n in target.childNodes if n.nodeType == Node.ELEMENT_NODE and n.tagName == item]
    if [n.firstChild.nodeValue if n.firstChild else "" for n in old] == values:
        return
    for node in list(target.childNodes):
        if node in old or (node.nodeType == Node.TEXT_NODE and not node.data.strip()):
            target.removeChild(node)
    doc = parent.ownerDocument
    for value in values:
        target.appendChild(doc.createTextNode("\n      "))
        child = doc.createElement(item)
        child.appendChild(doc.createTextNode(value))
        target.appendChild(child)
    target.appendChild(doc.createTextNode("\n    "))


def configure(source, component, address, settings=None):
    def connection(node):
        if component == "server":
            set_value(node, "disabled", "no")
            set_value(node, "remote_enrollment", "no")
        else:
            server = ensure_element(node, "server", 4)
            set_value(server, "address", address, 6)
            set_value(server, "port", "1514", 6)
            set_value(server, "protocol", "tcp", 6)
            set_value(ensure_element(node, "enrollment", 4), "enabled", "no", 6)
    source = edit_section(source, "auth" if component == "server" else "client", connection)
    if not settings:
        return source

    def cluster(node):
        for name in ("name", "node_name", "node_type", "key", "disabled", "bind_addr"):
            set_value(node, name, settings[name])
        set_list(node, "nodes", "node", [settings["master"]])

    def indexer(node):
        set_value(node, "enabled", "yes")
        set_list(node, "hosts", "host", settings["indexers"])
        if "indexer_ca" in settings:
            set_list(ensure_element(node, "ssl", 4), "certificate_authorities", "ca", [settings["indexer_ca"]])

    return edit_section(edit_section(source, "cluster", cluster), "indexer", indexer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=["server", "agent"])
    parser.add_argument("--address")
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--config", type=Path, default=Path("/var/ossec/etc/ossec.conf"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.component == "agent" and not args.address:
        parser.error("--address is required for an agent")
    path = args.config.resolve(strict=True)
    original = path.read_bytes().decode("utf-8")
    updated = configure(original, args.component, args.address, json.loads(args.settings.read_text()) if args.settings else None)
    if updated == original:
        print("ok")
        return
    if not args.check:
        metadata = path.stat()
        with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as temp:
            temp_path = Path(temp.name)
        try:
            temp_path.write_bytes(updated.encode("utf-8"))
            if args.component == "agent":
                subprocess.run(["/var/ossec/bin/wazuh-agentd", "-t", "-c", str(temp_path)], check=True)
            os.chown(temp_path, metadata.st_uid, metadata.st_gid)
            shutil.copystat(path, temp_path)
            os.utime(temp_path, None)
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
    print("changed")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ExpatError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
