param([string]$Ref = "upstream/4.7")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    if (git status --porcelain) { throw "Commit or stash your local edits before updating." }
    git fetch upstream --tags
    if ($LASTEXITCODE) { throw "Fetch failed" }
    git merge --no-edit $Ref
    if ($LASTEXITCODE) { throw "Merge needs attention. Resolve it before rebuilding; no reset or force-push was performed." }
    Write-Host "Merged $Ref. Run ./build-local.ps1, test, then git push."
} finally { Pop-Location }
