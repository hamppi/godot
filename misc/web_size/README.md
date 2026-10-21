# Minimal Kenney web builds

Measured 2026-10-22, Godot 4.7.2. The full Windows editor keeps its features; only the
per-game release runtimes are trimmed. Each game carries its template, profile and SHA-256 manifest.
See GameHub/docs/GODOT-WEB-SIZES.md for the before/after results and test limitations.

## Rebuild

On the Mac, with Emscripten 6.0.10 and the GodotTools Python/SCons environment:

```sh
bash ~/Godot/misc/web_size/build-templates.sh
bash ~/Godot/misc/web_size/export-candidates.sh
python3 ~/Godot/misc/web_size/describe_template.py ~/HTML5Games/GodotGames
for p in ~/HTML5Games/GodotGames/Starter-Kit-*; do
  ~/GodotTools/build-venv/bin/python ~/Godot/misc/web_size/package_web.py "$p" --candidate
done
```

`build-templates.sh FPS` and the export script accept individual kit suffixes.
The build uses `modules_enabled_by_default=no` on the SCons command line: putting this
only in a build profile is too late for default module selection. It uses full LTO,
`optimize=size_extra`, Closure, single threading and no dynamic linking, assertions,
debug symbols or JavaScript eval. Required JS bridge functionality is also omitted;
add it and rebuild before introducing portal SDK integration.

Profiles are manual module allowlists plus native resource/class scans. Do not apply a
profile to a stock template and expect a smaller WASM: compile it. `scan-project.gd`
also finds native class tokens and literal resource paths in scripts; retain explicit
export entries for runtime-loaded assets such as FPS impact scenes and City sample maps.
`prepare_profiles.py` consumes scans saved in size-research/dependencies; review the
result before recompilation. Static scanning cannot prove arbitrary dynamic loads safe.

Each game's build-web.ps1 performs native import and feature checks, validates the
template/profile hashes, exports release and verifies the actual WASM hash. A changed
feature set requires rebuilding the template; it never silently falls back to stock.
Debug exports intentionally retain the installed official template.

## Preserve behavior and validate

Profiles keep Jolt for Racing/Platformer, GodotPhysics3D for FPS, 2D physics for Match-3,
GridMap for Racing/City, required text and audio modules. Basic Scene replaces a simple
CSG floor with an equivalent BoxMesh to omit CSG. The two large skies use Basis Universal
at their original resolution, avoiding separate ASTC/BPTC copies. Basis compression is
lossy; source images stay intact and the result must be visually reviewed.
Complex text shaping, unused codecs, navigation, XR, importers and other unused features
are omitted. Restore modules/classes as needed for new mechanics, fonts or languages.

Before promotion, test all six in headed Chrome on the Mac. Test swaps, driving,
platformer movement/jump, FPS firing/weapon changes and City placement/save/load after
reload plus its sample map. Basic Scene is static. Inspect screenshots and HTTP failures.
The existing macOS automated pointer-lock focus limitation must be reported separately;
use the Windows functional pointer-lock check as additional evidence, not manual play proof.
Frame callback cadence is not a low-end phone benchmark.

`make_qa_server.py` runs an isolated ephemeral Game Hub fixture, leaving live previews alone.
`promote.py <GodotGames>` requires a successful six-game QA report and retains old builds
under size-research/previous-live-builds. The size-research directory is ignored research
evidence, not required engine source. `audit.py` records file hashes and PCK member sizes.

Packaging generates upload/game-build.zip in a dedicated upload/ directory containing
only that ZIP. Its allowlist includes runtime files and the license, excluding project sources,
templates, Hub metadata/artwork and all .br/.gz copies. Unpacked binaries and optional
Brotli-11/gzip-9 HTTP sidecars stay in web-build/ for local previews. --upload-only recreates
the final ZIP without rebuilding or recompressing the preview. Install Python `brotli` to regenerate Brotli. The Hub serves
sidecars with negotiated Content-Encoding; other hosts need their own encoding configuration.
Compare decoded WASM size, encoded transfer size and upload ZIP size separately.

## Research

- [Godot size optimization](https://docs.godotengine.org/en/4.7/engine_details/development/compiling/optimizing_for_size.html)
- [Compilation feature profiles and their limitations](https://docs.godotengine.org/en/4.7/tutorials/editor/using_engine_compilation_configuration_editor.html)
- [Web compilation](https://docs.godotengine.org/en/4.7/engine_details/development/compiling/compiling_for_web.html)
- [Image import and Basis Universal tradeoffs](https://docs.godotengine.org/en/4.7/tutorials/assets_pipeline/importing_images.html)
- [Historical 4.3 web report](https://godotengine.org/article/progress-report-web-export-in-4-3/): about 40 MB raw / 5 MB Brotli then; not a current size guarantee.
