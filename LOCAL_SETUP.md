# Your Windows Godot fork

Source: D:/Godot. Fork: https://github.com/hamppi/godot.
Upstream: https://github.com/godotengine/godot.
Working branch: codex/windows-4.7.2, based on official tag 4.7.2-stable.

Build with PowerShell: `./build-local.ps1` (Visual Studio 2022 C++, Windows SDK, Python and SCons).
The editor is `bin/godot.windows.editor.x86_64.exe`; the console version beside it is used for exports.
SCons also generates a Visual Studio solution for engine development.
Dependencies were installed with the official scripts in misc/scripts: install_d3d12_sdk_windows.py,
install_accesskit.py and install_angle.py. Vulkan, D3D12 and Compatibility renderers are retained.

Run `./sync-upstream.ps1` when you want an update from the official 4.7 maintenance branch.
The script requires a clean checkout and merges upstream without discarding your engine edits.
Choose a newer stable tag explicitly with `-Ref <tag>` after fetching tags; review, rebuild and test before pushing.
The upstream master branch is engine development, so it is not merged into this stable build automatically.

Kenney projects live in D:/HTML5Games/GodotGames. Open a project's project.godot in this editor.
Run each project's build-web.ps1 to import and export to web-build/index.html and game-build.zip.
Each kit ships its own audited minimal release template in web-templates/release.zip.
Official templates remain installed for debug exports. The Windows editor retains full engine features.
Changes to runtime code, enabled features or profiles require rebuilding the corresponding web template
with Emscripten and revalidating the game. See misc/web_size/README.md and the Game Hub size report.
