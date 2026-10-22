#!/usr/bin/env python3
"""Check actual Codex skills/list discovery without a model call or resume upload."""
import json
import selectors
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = subprocess.Popen(['codex', 'app-server', '--stdio'], stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
sel = selectors.DefaultSelector()
sel.register(p.stdout, selectors.EVENT_READ)

def rpc(message, expected):
    p.stdin.write(json.dumps(message)+'\n')
    p.stdin.flush()
    end = time.monotonic()+25
    while time.monotonic() < end:
        if not sel.select(1):
            if p.poll() is not None:
                raise RuntimeError('Codex app-server exited; check runtime filesystem permissions with codex doctor.')
            continue
        line = p.stdout.readline()
        if not line:
            raise RuntimeError('Codex app-server closed its output; runtime startup failed.')
        reply = json.loads(line)
        if reply.get('id') == expected:
            if 'error' in reply:
                raise RuntimeError(str(reply['error']))
            return reply['result']
    raise TimeoutError('Codex RPC timeout')

try:
    rpc({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'hiring-panel-check', 'version': '1.0.0'}}}, 1)
    p.stdin.write(json.dumps({'method': 'initialized', 'params': {}})+'\n')
    p.stdin.flush()
    result = rpc({'id': 2, 'method': 'skills/list', 'params': {'cwds': [str(ROOT)], 'forceReload': True}}, 2)
    matches = [s for entry in result.get('data', []) for s in entry.get('skills', []) if s.get('name') == 'hiring-panel']
    expected = ROOT/'.agents/skills/hiring-panel/SKILL.md'
    if not any(Path(s.get('path', '')).resolve() == expected and s.get('enabled', True) for s in matches):
        raise RuntimeError('Installed hiring-panel was not discovered as enabled.')
    print(f'PASS: Codex discovered hiring-panel at {expected}')
finally:
    sel.close()
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
