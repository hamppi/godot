"""Produce deterministic compact upload ZIPs and optional HTTP encoding sidecars."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

try:
    import brotli
except ImportError:
    brotli = None


def verify_template(project):
    expected = json.loads((project / 'web-templates/manifest.json').read_text(encoding='utf-8'))
    template = hashlib.sha256((project / 'web-templates/release.zip').read_bytes()).hexdigest()
    profile = json.loads((project / 'web-build-profile.gdbuild').read_text(encoding='utf-8'))
    profile_sha = hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if template != expected['template_sha256'] or profile_sha != expected['profile_sha256']:
        raise RuntimeError('The custom template/profile changed. Rebuild and validate the template; stock fallback is not allowed.')
    return expected


def package(project, candidate=False):
    build = project / ('.web-build-candidate' if candidate else 'web-build')
    expected = verify_template(project)
    actual = hashlib.sha256((build / 'index.wasm').read_bytes()).hexdigest()
    if actual != expected['wasm_sha256']:
        raise RuntimeError('Exported WASM differs from the audited small template. Refusing to package a fallback or stale build.')
    for name in ('LICENSE', 'LICENSE.txt', 'LICENSE.md'):
        if (project / name).is_file():
            (build / 'LICENSE.txt').write_bytes((project / name).read_bytes())
            break
    report = []
    for asset in sorted(build.iterdir()):
        if not asset.is_file() or asset.name.startswith('.') or asset.suffix in ('.br', '.gz'):
            continue
        data = asset.read_bytes()
        row = {'name': asset.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        if asset.suffix in ('.wasm', '.pck', '.js') and len(data) > 1024:
            encoded = {'.gz': gzip.compress(data, compresslevel=9, mtime=0)}
            if brotli:
                encoded['.br'] = brotli.compress(data, quality=11)
            for suffix, payload in encoded.items():
                side = asset.with_name(asset.name + suffix)
                if len(payload) < len(data):
                    side.write_bytes(payload)
                    row['brotli11' if suffix == '.br' else 'gzip9'] = len(payload)
                elif side.exists():
                    side.unlink()
        report.append(row)
    # Keep the Hub's artwork/metadata and HTTP sidecars out of upload archives.
    # Hosts receive ordinary files and apply their own Content-Encoding negotiation.
    archive = project / ('.candidate-game-build.zip' if candidate else 'game-build.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for asset in sorted(build.iterdir()):
            if not asset.is_file() or asset.name.startswith('.') or asset.name in ('hub.json', 'hub-cover.png') or asset.suffix in ('.br', '.gz'):
                continue
            info = zipfile.ZipInfo(asset.name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, asset.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    result = {'files': report, 'zip_bytes': archive.stat().st_size,
              'runtime_raw_bytes': sum(r['bytes'] for r in report if r['name'] not in ('hub.json', 'hub-cover.png')),
              'runtime_brotli_bytes': sum(r.get('brotli11', r['bytes']) for r in report if r['name'] not in ('hub.json', 'hub-cover.png'))}
    report_file = project / ('.candidate-web-size-report.json' if candidate else 'web-size-report.json')
    report_file.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"{project.name}: raw={result['runtime_raw_bytes']:,}, Brotli={result['runtime_brotli_bytes']:,}, ZIP={result['zip_bytes']:,}")
    if not brotli:
        print('Brotli sidecars unavailable: install the optional brotli Python package to generate them.')


if __name__ == '__main__':
    project = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    if '--verify-only' in sys.argv:
        verify_template(project)
        print('Custom template and profile verified')
    else:
        package(project, '--candidate' in sys.argv)
