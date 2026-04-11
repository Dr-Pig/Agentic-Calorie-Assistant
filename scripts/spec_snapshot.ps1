param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath
)

$ErrorActionPreference = "Stop"

$resolved = Resolve-Path -LiteralPath $FilePath
$fullPath = $resolved.Path

if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
    throw "File not found: $fullPath"
}

$root = Split-Path -Parent $PSScriptRoot
$auditRoot = Join-Path $root "docs\\_spec_snapshots"
if (-not (Test-Path -LiteralPath $auditRoot)) {
    New-Item -ItemType Directory -Path $auditRoot | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$fileName = [System.IO.Path]::GetFileName($fullPath)
$safeName = $fileName -replace '[^A-Za-z0-9._-]', '_'
$baseDir = Join-Path $auditRoot "${safeName}_${timestamp}"
New-Item -ItemType Directory -Path $baseDir | Out-Null

$snapshotPath = Join-Path $baseDir $fileName
$inventoryPath = Join-Path $baseDir "inventory.txt"
$metaPath = Join-Path $baseDir "meta.json"

Copy-Item -LiteralPath $fullPath -Destination $snapshotPath

$content = Get-Content -LiteralPath $fullPath
$headings = $content | Where-Object { $_ -match '^\s*#' }
$lineCount = $content.Count

$gitTracked = $false
try {
    $gitStatus = git ls-files --error-unmatch -- "$fullPath" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $gitTracked = $true
    }
} catch {
    $gitTracked = $false
}

@(
    "FILE: $fullPath"
    "SNAPSHOT: $snapshotPath"
    "LINES: $lineCount"
    "GIT_TRACKED: $gitTracked"
    ""
    "HEADINGS:"
    $headings
) | Set-Content -LiteralPath $inventoryPath -Encoding UTF8

$meta = [ordered]@{
    file = $fullPath
    snapshot = $snapshotPath
    line_count = $lineCount
    git_tracked = $gitTracked
    heading_count = $headings.Count
    created_at = (Get-Date).ToString("o")
}

$meta | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $metaPath -Encoding UTF8

Write-Output "Snapshot created:"
Write-Output $snapshotPath
Write-Output $inventoryPath
Write-Output $metaPath
