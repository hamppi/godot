#!/bin/bash
set -euo pipefail
engine="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$engine"
source "${EMSDK_HOME:-$HOME/Developer/emsdk}/emsdk_env.sh" >/dev/null 2>&1
python="${GODOT_BUILD_PYTHON:-$HOME/GodotTools/build-venv/bin/python}"
mkdir -p size-research/logs size-research/templates
if [ "$#" -gt 0 ]; then kits=("$@"); else kits=(Match-3 Basic-Scene City-Builder Racing 3D-Platformer FPS); fi
for kit in "${kits[@]}"; do
  echo "BUILD $kit $(date -u +%FT%TZ)"
  "$python" -m SCons platform=web target=template_release threads=no dlink_enabled=no modules_enabled_by_default=no \
    optimize=size_extra lto=full debug_symbols=no use_assertions=no javascript_eval=no use_closure_compiler=yes \
    build_profile="misc/web_size/profiles/$kit.gdbuild" -j3 \
    >"size-research/logs/$kit-build.log" 2>&1
  template="$(find bin -maxdepth 1 -name 'godot.web.template_release*.zip' -print | head -1)"
  test -n "$template"
  cp "$template" "size-research/templates/$kit.zip"
  "$python" -c 'import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); print([(i.filename,i.file_size,i.compress_size) for i in z.infolist() if i.filename.endswith((".wasm",".js"))])' "size-research/templates/$kit.zip"
  echo "DONE $kit $(date -u +%FT%TZ)"
done
