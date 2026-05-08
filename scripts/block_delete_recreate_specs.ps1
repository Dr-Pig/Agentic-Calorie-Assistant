Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ($env:LHC_ALLOW_SPEC_DELETE -eq "1") {
    Write-Output "spec-delete-blocker: override enabled via LHC_ALLOW_SPEC_DELETE=1"
    exit 0
}

$protectedExact = @(
    "AGENTS.md",
    "docs/DOC_INDEX.md",
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

function Is-ProtectedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.Replace("\", "/")

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

$raw = git diff --cached --name-status --find-renames=100%
if ($LASTEXITCODE -ne 0) {
    throw "spec-delete-blocker: failed to inspect staged diff"
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
    if ($parts.Count -lt 2) {
        continue
    }

    $status = $parts[0]

    if ($status -eq "D") {
        $path = $parts[1]
        if (Is-ProtectedPath -Path $path) {
            $blocked.Add("deleted protected doc: $path")
        }
        continue
    }

    if ($status.StartsWith("R")) {
        if ($parts.Count -ge 3) {
            $oldPath = $parts[1]
            $newPath = $parts[2]
            if ((Is-ProtectedPath -Path $oldPath) -or (Is-ProtectedPath -Path $newPath)) {
                $blocked.Add("renamed protected doc: $oldPath -> $newPath")
            }
        }
        continue
    }
}

if ($blocked.Count -gt 0) {
    Write-Error "spec-delete-blocker: protected documentation cannot be deleted or renamed in normal flow."
    foreach ($item in $blocked) {
        Write-Error "spec-delete-blocker: $item"
    }
    Write-Error "spec-delete-blocker: use additive edits or approved move flow."
    Write-Error "spec-delete-blocker: if deletion/rename is truly intentional, rerun commit with LHC_ALLOW_SPEC_DELETE=1 after taking snapshots and recording the reason."
    exit 1
}

exit 0
