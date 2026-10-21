"""Keep portal upload ZIPs separate from unpacked local previews and HTTP sidecars."""
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

RUNTIME_FILES = {
    'index.html', 'index.js', 'index.wasm', 'index.pck', 'index.png',
    'index.icon.png', 'index.apple-touch-icon.png', 'index.audio.worklet.js',
    'index.audio.position.worklet.js', 'LICENSE.txt',
}


def write_upload(project, build, candidate=False):
    expected = verify_template(project)
    if hashlib.sha256((build / 'index.wasm').read_bytes()).hexdigest() != expected['wasm_sha256']:
        raise RuntimeError('Exported WASM differs from the audited small template.')
    for name in ('index.html', 'index.js', 'index.wasm', 'index.pck', 'LICENSE.txt'):
        if not (build / name).is_file():
            raise RuntimeError(f'Missing required upload file: {name}')
    for asset in build.iterdir():
        if asset.suffix in ('.html', '.js', '.wasm', '.pck') and asset.name not in RUNTIME_FILES:
            raise RuntimeError(f'Unknown runtime file: {asset.name}. Review the upload allowlist.')
    archive = project / '.candidate-game-build.zip' if candidate else project / 'upload/game-build.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    temporary = project / '.upload-game-build.zip.tmp'
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name in sorted(RUNTIME_FILES):
                asset = build / name
                if not asset.is_file():
                    continue
                info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, asset.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:
                raise RuntimeError('Upload ZIP failed its integrity check')
        temporary.replace(archive)
    finally:
        if temporary.exists():
            temporary.unlink()
    # Retire the previous generated delivery path after the new archive is complete.
    legacy = project / 'game-build.zip'
    if not candidate and legacy.is_file():
        legacy.unlink()
    return archive


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
    archive = write_upload(project, build, candidate)
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
    elif '--upload-only' in sys.argv:
        archive = write_upload(project, project / 'web-build')
        print(f'Upload ready: {archive}')
    else:
        package(project, '--candidate' in sys.argv)
