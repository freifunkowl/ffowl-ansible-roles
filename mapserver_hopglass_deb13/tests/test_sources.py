#!/usr/bin/env python3
"""Check legacy APT migration matching without modifying host configuration."""
from pathlib import Path
import re
import yaml

role = Path(__file__).resolve().parents[1]
for path in role.rglob('*.yml'):
    yaml.safe_load(path.read_text())
tasks = yaml.safe_load((role / 'tasks/main.yml').read_text())
pattern = next(task['ansible.builtin.lineinfile']['regexp']
               for task in tasks if 'ansible.builtin.lineinfile' in task)
for line in [
    'deb [trusted=yes] https://deb.nodesource.com/node_16.x bullseye main',
    'deb-src [trusted=yes] https://deb.nodesource.com/node_16.x bookworm main',
    'deb  [trusted=yes] https://dl.yarnpkg.com/debian/ stable main',
    'deb https://dl.yarnpkg.com/debian stable main',
]:
    assert re.search(pattern, line), line
for line in [
    'deb https://deb.debian.org/debian trixie main',
    '# deb https://dl.yarnpkg.com/debian/ stable main',
    'deb https://deb.nodesource.com/node_22.x nodistro main',
]:
    assert not re.search(pattern, line), line
print('PASS: YAML parses; obsolete APT sources match; unrelated sources remain')
