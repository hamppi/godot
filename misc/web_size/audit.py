"""Measure raw files, compressed delivery sizes, ZIP size, and Godot PCK members."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

try:
    import brotli
except ImportError:
    brotli = None


def pck_members(path):
    with path.open('rb') as f:
        def read(fmt):
            return struct.unpack('<' + fmt, f.read(struct.calcsize('<' + fmt)))
        magic, version, major, minor, patch, flags = read('6I')
        if magic != 0x43504447 or flags & 1:
            raise ValueError('Unsupported or encrypted PCK')
        file_base, = read('Q')
        if version >= 3:
            directory, = read('Q')
            f.seek(directory)
        else:
            f.read(64)
        count, = read('I')
        entries = []
        for _ in range(count):
            length, = read('I')
            name = f.read(length).rstrip(b'\0').decode('utf-8')
            offset, size = read('QQ')
            f.read(16)
            entry_flags, = read('I')
            entries.append({'path': name, 'bytes': size, 'offset': file_base + offset, 'flags': entry_flags})
        return sorted(entries, key=lambda x: -x['bytes'])


def measure(root, output, backup=None):
    output.mkdir(parents=True, exist_ok=True)
    rows, compression_cache = [], {}
    for project in sorted(root.glob('Starter-Kit-*')):
        if not (project / 'project.godot').is_file():
            continue
        build = project / 'web-build'
        files = []
        for p in sorted(build.iterdir()):
            if not p.is_file() or p.name.startswith('.') or p.suffix in ('.br', '.gz'):
                continue
            data = p.read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            gz, br = p.with_name(p.name + '.gz'), p.with_name(p.name + '.br')
            if gz.exists() and br.exists() and min(gz.stat().st_mtime, br.stat().st_mtime) >= p.stat().st_mtime:
                compression_cache[sha] = {'gzip9': gz.stat().st_size, 'brotli11': br.stat().st_size}
            if sha not in compression_cache:
                compression_cache[sha] = {'gzip9': len(gzip.compress(data, compresslevel=9, mtime=0)),
                                          'brotli11': len(brotli.compress(data, quality=11)) if brotli else None}
            files.append({'name': p.name, 'bytes': len(data), 'sha256': sha, **compression_cache[sha]})
        members = pck_members(build / 'index.pck')
        (output / f'{project.name}-pck.json').write_text(json.dumps(members, indent=2), encoding='utf-8')
        row = {'game': project.name, 'files': files, 'raw_total': sum(f['bytes'] for f in files),
               'gzip9_total': sum(f['gzip9'] for f in files),
               'brotli11_total': sum(f['brotli11'] for f in files) if brotli else None,
               'zip_bytes': (project / 'game-build.zip').stat().st_size, 'pck_member_count': len(members)}
        rows.append(row)
        print(f"{project.name}: wasm={next(f['bytes'] for f in files if f['name']=='index.wasm'):,}; "
              f"PCK={(build/'index.pck').stat().st_size:,}; raw={row['raw_total']:,}; "
              f"gzip={row['gzip9_total']:,}; brotli={row['brotli11_total']}; zip={row['zip_bytes']:,}", flush=True)
        print('  Largest PCK resources:', [(x['path'], x['bytes']) for x in members[:4]], flush=True)
        if backup:
            backup.mkdir(parents=True, exist_ok=True)
            dest = backup / f'{project.name}.zip'
            if not dest.exists():
                shutil.copy2(project / 'game-build.zip', dest)
    (output / 'sizes.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    measure(args.root, args.output, args.backup)
