#!/bin/bash
set -euo pipefail
engine="$(cd "$(dirname "$0")/../.." && pwd)"
games="${GODOT_GAMES_ROOT:-$HOME/HTML5Games/GodotGames}"
godot="${GODOT_EDITOR:-$HOME/GodotTools/Godot.app/Contents/MacOS/Godot}"
if [ "$#" -gt 0 ]; then kits=("$@"); else kits=(Match-3 Basic-Scene City-Builder Racing 3D-Platformer FPS); fi
for kit in "${kits[@]}"; do
  project="$games/Starter-Kit-$kit"
  test -f "$engine/size-research/templates/$kit.zip"
  mkdir -p "$project/web-templates" "$project/.web-build-candidate"
  touch "$project/web-templates/.gdignore" "$project/.web-build-candidate/.gdignore"
  cp "$engine/size-research/templates/$kit.zip" "$project/web-templates/release.zip"
  cp "$engine/misc/web_size/profiles/$kit.gdbuild" "$project/web-build-profile.gdbuild"
  "$godot" --headless --editor --import --path "$project" > "$engine/size-research/logs/$kit-import.log" 2>&1
  "$godot" --headless --path "$project" --script res://tools/web-size/scan-project.gd -- res://.web-dependencies.json res://web-build-profile.gdbuild
  "$godot" --headless --path "$project" --export-release Web .web-build-candidate/index.html > "$engine/size-research/logs/$kit-export.log" 2>&1
  cp "$project/hub-web.json" "$project/.web-build-candidate/hub.json"
  cp "$project/screenshots/screenshot.png" "$project/.web-build-candidate/hub-cover.png"
  echo "EXPORTED $kit"
done
