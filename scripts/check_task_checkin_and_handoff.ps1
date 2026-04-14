param(
    [switch]$AuditRepo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Normalize-Path {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path.Replace("\", "/")
}

function Get-RepoArtifactPaths {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Directories
    )

    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($directory in $Directories) {
        $absoluteDirectory = Join-Path $repoRoot $directory
        if (-not (Test-Path -LiteralPath $absoluteDirectory)) {
            continue
        }

        Get-ChildItem -LiteralPath $absoluteDirectory -Filter *.md -File | ForEach-Object {
            if ($_.Name -ne "README.md") {
                $relative = $_.FullName.Substring($repoRoot.Length + 1)
                $paths.Add((Normalize-Path -Path $relative))
            }
        }
    }

    return @($paths)
}

function Test-ArtifactContainsAny {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string[]]$Hints
    )

    foreach ($hint in $Hints) {
        if ($Content -match [Regex]::Escape($hint)) {
            return $true
        }
    }

    return $false
}

$artifactDirs = @(
    "docs/exec-plans/active/tasks/",
    "docs/exec-plans/completed/tasks/",
    "docs/exec-plans/active/handoff/",
    "docs/exec-plans/completed/handoff/"
)

$paths = if ($AuditRepo) {
    @(Get-RepoArtifactPaths -Directories $artifactDirs)
}
else {
    $rawPaths = git diff --cached --name-only --diff-filter=ACMR
    if ($LASTEXITCODE -ne 0) {
        throw "task-handoff-check: failed to inspect staged paths"
    }

    if ([string]::IsNullOrWhiteSpace($rawPaths)) {
        exit 0
    }

    @($rawPaths -split "`r?`n" | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_)
    } | ForEach-Object {
        Normalize-Path -Path $_
    } | Where-Object {
        $p = $_
        $artifactDirs | Where-Object { $p.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) }
    })
}

if ($paths.Count -eq 0) {
    exit 0
}

$issues = New-Object System.Collections.Generic.List[string]
$taskHints = @('task_id', 'slice_id', 'status', 'goal', 'required_harness', 'next_action')
$handoffHints = @('handoff_id', 'current_status', 'what_changed', 'next_recommended_action')

foreach ($path in $paths) {
    $absolute = Join-Path $repoRoot $path
    if (-not (Test-Path -LiteralPath $absolute)) {
        $issues.Add("artifact '$path' is missing from the working tree.")
        continue
    }

    $content = [System.IO.File]::ReadAllText($absolute)

    if ($path.StartsWith("docs/exec-plans/", [System.StringComparison]::OrdinalIgnoreCase)) {
        if (-not (Test-ArtifactContainsAny -Content $content -Hints $taskHints)) {
            $issues.Add("task artifact '$path' does not appear to contain the lean optional-task fields from docs/governance/TASK_CHECKIN_PROTOCOL.md.")
        }
    }
    elseif ($path.StartsWith("docs/exec-plans/active/handoff/", [System.StringComparison]::OrdinalIgnoreCase) -or
            $path.StartsWith("docs/exec-plans/completed/handoff/", [System.StringComparison]::OrdinalIgnoreCase)) {
        if (-not (Test-ArtifactContainsAny -Content $content -Hints $handoffHints)) {
            $issues.Add("handoff artifact '$path' does not appear to contain the lean optional-handoff fields from docs/governance/HANDOFF_CONTRACT.md.")
        }
    }
}

if ($issues.Count -gt 0) {
    Write-Warning "task-handoff-check: advisory compatibility audit only; this script no longer blocks CI or pre-commit by default."
    foreach ($issue in $issues) {
        Write-Warning "task-handoff-check: $issue"
    }
}

exit 0
