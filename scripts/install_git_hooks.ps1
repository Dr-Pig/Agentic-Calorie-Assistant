Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$hooksPath = ".githooks"

git -C $repoRoot config core.hooksPath $hooksPath

$runtimeDirs = @(
    (Join-Path $repoRoot "runtime"),
    (Join-Path $repoRoot "runtime\db"),
    (Join-Path $repoRoot "runtime\logs"),
    (Join-Path $repoRoot "runtime\artifacts\session_records"),
    (Join-Path $repoRoot "workspace_data")
)

foreach ($dir in $runtimeDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Output "Installed git hooks path: $hooksPath (pre-commit + commit-msg)"
Write-Output "Ensured runtime directories exist."
Write-Output "If you installed Python tooling, run 'pre-commit install --install-hooks' and 'pre-commit run --all-files'."
