"""Run an isolated Game Hub fixture for candidate builds without restarting the live Hub."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

engine = Path(__file__).resolve().parents[2]
folder = engine / 'size-research/qa-server'
if '--stop' in sys.argv:
    pid = int((folder / 'pid').read_text())
    command = subprocess.check_output(['ps', '-p', str(pid), '-o', 'command='], text=True)
    if str(folder / 'server.js') not in command:
        raise RuntimeError('PID no longer belongs to the QA fixture')
    os.kill(pid, 15)
    raise SystemExit()
hub = Path.home() / 'HTML5Games/GameHub'
games = Path.home() / 'HTML5Games/GodotGames'
folder.mkdir(parents=True, exist_ok=True)
for name in ('server.js', 'iap_scan.mjs', 'lan-tls.mjs', 'versions.mjs'):
    shutil.copy2(hub / name, folder / name)
(folder / 'package.json').write_text('{"type":"module"}')
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
kits = ('Match-3', 'Basic-Scene', 'City-Builder', 'Racing', '3D-Platformer', 'FPS')
config = {'port': port, 'lan': False, 'roots': [
    {'label': 'Godot-' + kit, 'kind': 'static', 'path': str(games / ('Starter-Kit-' + kit) / '.web-build-candidate'),
     'depth': 0, 'includeSelf': True} for kit in kits], 'exclude': [], 'names': {}}
(folder / 'hub.config.json').write_text(json.dumps(config))
env = dict(os.environ, GAMEHUB_CONFIG=str(folder / 'hub.config.json'))
with (folder / 'server.log').open('w') as log:
    child = subprocess.Popen(['node', str(folder / 'server.js')], cwd=folder, stdout=log, stderr=log,
                             env=env, start_new_session=True)
(folder / 'pid').write_text(str(child.pid))
url = f'http://127.0.0.1:{port}'
(folder / 'url').write_text(url)
for _ in range(100):
    try:
        with urllib.request.urlopen(url + '/api/games', timeout=1):
            break
    except Exception:
        if child.poll() is not None:
            raise RuntimeError((folder / 'server.log').read_text())
        time.sleep(.1)
print(url, flush=True)
