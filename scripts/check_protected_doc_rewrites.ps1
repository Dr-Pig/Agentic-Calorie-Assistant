Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ($env:LHC_ALLOW_PROTECTED_REWRITE -eq "1") {
    Write-Output "protected-doc-rewrite-check: override enabled via LHC_ALLOW_PROTECTED_REWRITE=1"
    exit 0
}

$protectedExact = @(
    "AGENTS.md",
    "docs/index.md",
    "docs/governance/ENCODING_POLICY.md",
    "docs/governance/SPEC_EDITING_PROTOCOL.md",
    "docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md",
    "docs/governance/TASK_CHECKIN_PROTOCOL.md",
    "docs/governance/HANDOFF_CONTRACT.md"
)

$protectedPrefixes = @(
    "docs/specs/",
    "docs/quality/"
)

function Normalize-Path {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path.Replace("\", "/")
}

function Is-ProtectedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = Normalize-Path -Path $Path

    foreach ($exact in $protectedExact) {
        if ($normalized -ieq $exact) {
            return $true
        }
    }

    foreach ($prefix in $protectedPrefixes) {
        if ($normalized.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Get-LineCount {
    param(
        [string]$Content
    )

    if ([string]::IsNullOrEmpty($Content)) {
        return 0
    }

    return ($Content -replace "`r`n", "`n").Split("`n").Length
}

function Test-GitObjectExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Spec
    )

    cmd /c "git cat-file -e ""$Spec"" 2>nul" | Out-Null
    return ($LASTEXITCODE -eq 0)
}

$raw = git diff --cached --numstat --diff-filter=AM
if ($LASTEXITCODE -ne 0) {
    throw "protected-doc-rewrite-check: failed to inspect staged diff"
}

if ([string]::IsNullOrWhiteSpace($raw)) {
    exit 0
}

$blocked = New-Object System.Collections.Generic.List[string]

foreach ($line in ($raw -split "`r?`n")) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }

    $parts = $line -split "`t"
    if ($parts.Count -lt 3) {
        continue
    }

    $addedRaw = $parts[0]
    $deletedRaw = $parts[1]
    $path = Normalize-Path -Path $parts[2]

    if (-not (Is-ProtectedPath -Path $path)) {
        continue
    }

    if ($addedRaw -eq "-" -or $deletedRaw -eq "-") {
        continue
    }

    $added = [int]$addedRaw
    $deleted = [int]$deletedRaw

    if ($added -eq 0 -and $deleted -eq 0) {
        continue
    }

    $hadOld = Test-GitObjectExists -Spec "HEAD:$path"
    if (-not $hadOld) {
        continue
    }

    if (-not (Test-GitObjectExists -Spec ":$path")) {
        continue
    }

    $oldContent = git show "HEAD:$path" 2>$null | Out-String
    $newContent = git show ":$path" 2>$null | Out-String

    $oldLines = Get-LineCount -Content $oldContent
    $newLines = Get-LineCount -Content $newContent

    if ($oldLines -le 0 -or $newLines -le 0) {
        continue
    }

    $deleteRatio = [double]$deleted / [double]$oldLines
    $addRatio = [double]$added / [double]$newLines

    if ($deleteRatio -ge 0.80 -and $addRatio -ge 0.80) {
        $blocked.Add("$path (deleted $deleted/$oldLines lines, added $added/$newLines lines)")
    }
}

if ($blocked.Count -gt 0) {
    Write-Error "protected-doc-rewrite-check: suspicious near-total rewrite detected for protected docs."
    foreach ($item in $blocked) {
        Write-Error "protected-doc-rewrite-check: $item"
    }
    Write-Error "protected-doc-rewrite-check: use section-level patches by default."
    Write-Error "protected-doc-rewrite-check: if a rewrite is explicitly approved, record a content inventory and rerun with LHC_ALLOW_PROTECTED_REWRITE=1."
    exit 1
}

exit 0
