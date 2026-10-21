"""Record template provenance and verify the release WASM used by subsequent exports."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

engine = Path(__file__).resolve().parents[2]
games = Path(sys.argv[1]).resolve()
kits = sys.argv[2:] or ['Match-3', 'Racing', '3D-Platformer', 'FPS', 'City-Builder', 'Basic-Scene']
for kit in kits:
    project = games / ('Starter-Kit-' + kit)
    template = project / 'web-templates/release.zip'
    profile = project / 'web-build-profile.gdbuild'
    with zipfile.ZipFile(template) as z:
        wasm_name = next(name for name in z.namelist() if name.endswith('.wasm'))
        wasm = z.read(wasm_name)
    info = {'godot_version': '4.7.2', 'upstream_tag': '4.7.2-stable',
            'upstream_commit': 'ed1daf0bf0', 'engine_fork': 'https://github.com/hamppi/godot',
            'engine_fixes': '7c24395199', 'emscripten': '6.0.10',
            'flags': {'platform': 'web', 'target': 'template_release', 'threads': False,
                      'dlink_enabled': False, 'modules_enabled_by_default': False, 'optimize': 'size_extra',
                      'lto': 'full', 'debug_symbols': False, 'use_assertions': False,
                      'javascript_eval': False, 'use_closure_compiler': True},
            'profile_sha256': hashlib.sha256(json.dumps(json.loads(profile.read_text()), sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'template_sha256': hashlib.sha256(template.read_bytes()).hexdigest(),
            'wasm_sha256': hashlib.sha256(wasm).hexdigest(), 'wasm_bytes': len(wasm)}
    (template.parent / 'manifest.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    print(kit, info['wasm_bytes'], info['template_sha256'][:16])
