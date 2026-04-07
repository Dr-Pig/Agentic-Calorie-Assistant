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

Write-Output "Installed git hooks path: $hooksPath"
Write-Output "Ensured runtime directories exist."
