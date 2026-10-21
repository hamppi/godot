param([int]$Jobs = 8)
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & python -m SCons platform=windows target=editor arch=x86_64 "-j$Jobs"
    if ($LASTEXITCODE) { throw "Godot build failed ($LASTEXITCODE)" }
    & ./bin/godot.windows.editor.x86_64.console.exe --headless --version
} finally { Pop-Location }
