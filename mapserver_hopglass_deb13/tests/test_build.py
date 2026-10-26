#!/usr/bin/env python3
"""Exercise the real build tasks locally; npm/node are isolated command doubles.
No apt, accounts, sudo, remote host or external registry is touched.
Requires ansible-playbook on PATH and PyYAML.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROLE = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="hopglass-role-test-") as temp:
    root = Path(temp)
    client = root / "client"
    bindir = root / "bin"
    bindir.mkdir()
    (client / "scripts").mkdir(parents=True)
    (client / "package-lock.json").write_text('{}\n')
    (client / "scripts/build.cjs").write_text('// fixture\n')
    (client / "build/config").mkdir(parents=True)
    (client / "build/config.json").write_text('{"preserve":true}\n')
    (client / "build/config/domain.json").write_text('{}\n')
    (bindir / "node").write_text('#!/bin/sh\nprintf "v20.19.2\\n"\n')
    npm = bindir / "npm"
    npm.write_text(f'''#!{sys.executable}
import pathlib, sys
p = pathlib.Path.cwd()
args = sys.argv[1:]
if args == ['--version']:
    print('9.2.0')
    raise SystemExit(0)
with (p / 'commands.log').open('a') as f:
    f.write(' '.join(args) + '\\n')
if args[0] == 'ci':
    (p / 'node_modules').mkdir(exist_ok=True)
elif args == ['run', 'build']:
    if (p / 'fail-build').exists():
        raise SystemExit(42)
    (p / 'build').mkdir(exist_ok=True)
    for name in ['app.js', 'style.css', 'index.html']:
        (p / 'build' / name).write_text('fixture')
''')
    for executable in bindir.iterdir():
        executable.chmod(0o755)
    playbook = root / "test.json"
    playbook.write_text(json.dumps([{
        "name": "Exercise actual build tasks", "hosts": "localhost",
        "gather_facts": False,
        "environment": {"PATH": str(bindir) + os.pathsep + os.environ['PATH']},
        "vars": {"ansible_connection": "local", "ansible_python_interpreter": sys.executable,
                 "hopglass_client_dir": str(client), "hopglass_client_git": {"after": "a" * 40},
                 "hopglass_client_force_build": False, "hopglass_client_run_tests": True},
        "tasks": [{"ansible.builtin.include_tasks": str(ROLE / "tasks/build.yml")}]
    }]))
    def run(success=True, extra=None):
        args = ['ansible-playbook', '-vv', '-i', 'localhost,', str(playbook)]
        if extra:
            args += ['-e', json.dumps(extra)]
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if (result.returncode == 0) != success:
            raise AssertionError(result.stdout)
        return result.stdout
    def commands():
        return (client / 'commands.log').read_text().splitlines()
    run()
    assert commands() == ['ci --ignore-scripts --include=dev --no-audit --no-fund', 'test', 'run build']
    count = len(commands())
    run()
    assert len(commands()) == count, 'unchanged second run rebuilt'
    print('PASS: initial build and unchanged second run')
    (client / 'build/app.js').unlink()
    run()
    assert len(commands()) == count + 3
    print('PASS: missing output triggers rebuild')
    (client / 'package-lock.json').write_text('{"lockfileVersion":3}\n')
    run()
    assert len(commands()) == count + 6
    print('PASS: lockfile change triggers rebuild')
    run(extra={'hopglass_client_git': {'after': 'b' * 40}})
    assert len(commands()) == count + 9
    print('PASS: source revision change triggers rebuild')
    (client / 'fail-build').touch()
    run(False, {'hopglass_client_force_build': True})
    assert not (client / '.ansible-npm-build').exists()
    (client / 'fail-build').unlink()
    run()
    assert (client / '.ansible-npm-build').exists()
    print('PASS: failure invalidates marker; next run retries')
    assert (client / 'build/config.json').read_text() == '{"preserve":true}\n'
    assert (client / 'build/config/domain.json').read_text() == '{}\n'
    print('PASS: role leaves operator configuration in place')
    (client / 'package-lock.json').unlink()
    before = len(commands())
    assert not (client / 'package-lock.json').exists()
    output = run(False)
    assert 'lacks package-lock.json' in output
    assert len(commands()) == before
    print('PASS: legacy checkout fails before npm commands')
