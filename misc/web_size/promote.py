"""Atomically promote validated candidates, retaining the previous builds for rollback."""
import datetime
import json
from pathlib import Path
import shutil
import sys
import time

engine = Path(__file__).resolve().parents[2]
root = Path(sys.argv[1]).resolve()
if root.name != 'GodotGames' or not root.is_dir():
    raise RuntimeError('Expected the explicitly selected GodotGames directory')
qa = json.loads((engine / 'size-research/qa-final/report.json').read_text())
if len(qa) != 6 or any(r['blockingErrors'] or r['failed'] for r in qa):
    raise RuntimeError('All six candidate browser checks must complete before promotion')
backup_root = (engine / 'size-research/previous-live-builds').resolve()
backup_root.mkdir(parents=True, exist_ok=True)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + str(time.time_ns())
for kit in ('Match-3', 'Racing', '3D-Platformer', 'FPS', 'City-Builder', 'Basic-Scene'):
    project = (root / ('Starter-Kit-' + kit)).resolve()
    candidate = (project / '.web-build-candidate').resolve()
    live = (project / 'web-build').resolve()
    backup = (backup_root / (project.name + '-' + stamp)).resolve()
    assert project.parent == root and candidate.parent == project and live.parent == project
    assert backup.parent == backup_root
    for name in ('index.html', 'index.wasm', 'index.pck'):
        if not (candidate / name).is_file():
            raise RuntimeError(f'Incomplete candidate: {candidate / name}')
    if not (project / '.candidate-game-build.zip').is_file():
        raise RuntimeError('Package candidate before promotion')
    if live.exists():
        live.rename(backup)
        if (project / 'upload/game-build.zip').exists():
            shutil.copy2(project / 'upload/game-build.zip', backup / 'previous-game-build.zip')
    candidate.rename(live)
    (project / 'upload').mkdir(exist_ok=True)
    (project / '.candidate-game-build.zip').replace(project / 'upload/game-build.zip')
    (project / '.candidate-web-size-report.json').replace(project / 'web-size-report.json')
    print('PROMOTED', kit, flush=True)
