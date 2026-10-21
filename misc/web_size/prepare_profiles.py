"""Apply audited class detection to checked-in, per-game module allowlists."""
import json
from pathlib import Path

engine = Path(__file__).resolve().parents[2]
deps = engine / 'size-research/dependencies'
profiles = engine / 'misc/web_size/profiles'
for filename in deps.glob('*.json'):
    info = json.loads(filename.read_text())
    p = profiles / (filename.stem + '.gdbuild')
    profile = json.loads(p.read_text())
    # Internal resources/default theme and dialog widgets may be constructed by C++.
    forced = {'Theme', 'Gradient', 'AudioBusLayout', 'CameraAttributes', 'MissingResource', 'MissingNode',
              'Shortcut', 'ButtonGroup', 'AudioStreamPolyphonic', 'AudioStreamRandomizer',
              'BaseButton', 'Button', 'LineEdit', 'Range', 'ScrollBar', 'HScrollBar', 'VScrollBar',
              'OptionButton', 'Tree', 'TreeItem', 'PopupMenu'}
    profile['disabled_classes'] = [c for c in info['disabled_classes'] if c not in forced]
    if filename.stem in ('3D-Platformer', 'FPS'):
        profile['disabled_build_options']['module_basis_universal_enabled'] = True
    p.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')
    print(filename.stem, 'disabled class roots:', len(profile['disabled_classes']))
