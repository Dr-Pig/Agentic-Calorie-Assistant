param(
    [switch]$AuditRepo
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$mode = $env:LHC_TASK_HANDOFF_ENFORCEMENT
if ([string]::IsNullOrWhiteSpace($mode)) {
    $mode = "warn"
}
$mode = $mode.ToLowerInvariant()

if ($mode -notin @("warn", "block")) {
    Write-Error "task-handoff-check: unsupported mode '$mode'. Use 'warn' or 'block'."
    exit 1
}

function Write-Issue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Warning "task-handoff-check: $Message"
}

function Add-Issue {
    param(
        [System.Collections.Generic.List[string]]$Issues,
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $Issues.Add($Message)
    Write-Issue -Message $Message
}

function Normalize-Path {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path.Replace("\", "/")
}

function Test-RequiredTokens {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string[]]$Tokens
    )

    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($token in $Tokens) {
        if ($Content -notmatch [Regex]::Escape($token)) {
            $missing.Add($token)
        }
    }
    return $missing
}

function Test-StructuredListHasEntries {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content,
        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $lines = ($Content -replace "`r`n", "`n").Split("`n")
    $needleA = "- ``${Key}``:"
    $needleB = "- `${Key}`:"
    $needleC = "- ${Key}:"

    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i].TrimEnd()
        if ($line -eq $needleA -or $line -eq $needleB -or $line -eq $needleC) {
            for ($j = $i + 1; $j -lt $lines.Length; $j++) {
                $next = $lines[$j]
                if ([string]::IsNullOrWhiteSpace($next)) {
                    continue
                }
                if ($next -match '^\s*-\s+') {
                    return $true
                }
                if ($next -match '^\S') {
                    return $false
                }
            }
        }
    }

    return $false
}

function Get-TaskStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    if ($Content -match '`status`:\s*`?([A-Z_]+)`?') {
        return $Matches[1]
    }

    return $null
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

$stagedPaths = @()
if (-not $AuditRepo) {
    $rawPaths = git diff --cached --name-only --diff-filter=ACMR
    if ($LASTEXITCODE -ne 0) {
        throw "task-handoff-check: failed to inspect staged paths"
    }

    if ([string]::IsNullOrWhiteSpace($rawPaths)) {
        exit 0
    }

    foreach ($line in ($rawPaths -split "`r?`n")) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $stagedPaths += (Normalize-Path -Path $line)
        }
    }
}

$issues = New-Object System.Collections.Generic.List[string]

$codePrefixes = @("app/", "tests/")
$taskPrefixes = @("docs/exec-plans/active/tasks/", "docs/exec-plans/completed/tasks/")
$handoffPrefixes = @("docs/handoff/active/", "docs/handoff/completed/")

$codePaths = @($stagedPaths | Where-Object {
    $p = $_
    $codePrefixes | Where-Object { $p.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) }
})
$taskPaths = if ($AuditRepo) {
    @(Get-RepoArtifactPaths -Directories $taskPrefixes)
}
else {
    @($stagedPaths | Where-Object {
        $p = $_
        $taskPrefixes | Where-Object { $p.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) }
    })
}
$handoffPaths = if ($AuditRepo) {
    @(Get-RepoArtifactPaths -Directories $handoffPrefixes)
}
else {
    @($stagedPaths | Where-Object {
        $p = $_
        $handoffPrefixes | Where-Object { $p.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) }
    })
}

if (-not $AuditRepo -and $codePaths.Count -gt 0 -and $taskPaths.Count -eq 0) {
    Add-Issue -Issues $issues -Message "staged code changes under app/tests without a staged task artifact in docs/exec-plans/active/tasks or completed/tasks."
}

$activeTaskRequiredTokens = @(
    'task_id',
    'slice_id',
    'status',
    'owner',
    'started_at',
    "## Source Of Truth Refs",
    "## Planned Touch Files",
    "## Forbidden Files",
    "## Goal",
    "## Completion Criteria",
    "## Tests To Run",
    "## Expected Re-plan Impact"
)

$handoffRequiredTokens = @(
    'handoff_id',
    'task_id',
    'slice_id',
    'current_status',
    "## What Changed",
    "## What Did Not Change",
    "## Files Touched",
    "## Blockers",
    "## Tests Run",
    "## Source Of Truth Docs Touched",
    "## Reality Drift",
    "## Next Recommended Action",
    "## Unsafe Assumptions To Avoid"
)

foreach ($taskPath in $taskPaths) {
    $absolute = Join-Path $repoRoot $taskPath
    if (-not (Test-Path -LiteralPath $absolute)) {
        Add-Issue -Issues $issues -Message "task artifact '$taskPath' is missing from working tree."
        continue
    }

    $content = [System.IO.File]::ReadAllText($absolute)
    $taskStatus = Get-TaskStatus -Content $content
    $missing = @(Test-RequiredTokens -Content $content -Tokens $activeTaskRequiredTokens)
    if ($missing.Count -gt 0) {
        Add-Issue -Issues $issues -Message "task artifact '$taskPath' is missing required sections or fields: $($missing -join ', ')"
    }

    if ($taskStatus -eq "COMPLETED") {
        if ($taskPath.StartsWith("docs/exec-plans/active/tasks/", [System.StringComparison]::OrdinalIgnoreCase)) {
            Add-Issue -Issues $issues -Message "completed task artifact '$taskPath' must be archived under docs/exec-plans/completed/tasks/ instead of remaining in active/tasks."
        }

        $completionRequiredTokens = @(
            'completed_at',
            'actual_touch_files',
            'tests_run',
            'reality_drift_notes',
            'source_of_truth_updated',
            'followup_task_ids',
            'handoff_doc_path'
        )
        $completionMissing = @(Test-RequiredTokens -Content $content -Tokens $completionRequiredTokens)
        if ($completionMissing.Count -gt 0) {
            Add-Issue -Issues $issues -Message "completed task artifact '$taskPath' is missing structured completion fields: $($completionMissing -join ', ')"
        }

        if (-not (Test-StructuredListHasEntries -Content $content -Key 'actual_touch_files[]')) {
            Add-Issue -Issues $issues -Message "completed task artifact '$taskPath' must include at least one structured actual_touch_files[] entry."
        }

        if (-not (Test-StructuredListHasEntries -Content $content -Key 'tests_run[]')) {
            Add-Issue -Issues $issues -Message "completed task artifact '$taskPath' must include at least one structured tests_run[] entry."
        }
    }

    if ($taskStatus -match "^(BLOCKED|HANDOFF|HANDOFF_NEEDED)$") {
        if ($handoffPaths.Count -eq 0 -and $content -notmatch "handoff_doc_path") {
            Add-Issue -Issues $issues -Message "task artifact '$taskPath' signals handoff/blocking state but no staged handoff doc or handoff_doc_path is present."
        }
    }
}

foreach ($handoffPath in $handoffPaths) {
    $absolute = Join-Path $repoRoot $handoffPath
    if (-not (Test-Path -LiteralPath $absolute)) {
        Add-Issue -Issues $issues -Message "staged handoff doc '$handoffPath' is missing from working tree."
        continue
    }

    $content = [System.IO.File]::ReadAllText($absolute)
    $missing = @(Test-RequiredTokens -Content $content -Tokens $handoffRequiredTokens)
    if ($missing.Count -gt 0) {
        Add-Issue -Issues $issues -Message "handoff doc '$handoffPath' is missing required sections or fields: $($missing -join ', ')"
    }

    if ($handoffPath.StartsWith("docs/handoff/active/", [System.StringComparison]::OrdinalIgnoreCase)) {
        $taskId = $null
        if ($content -match '`task_id`:\s*`?([A-Z0-9\-]+)`?') {
            $taskId = $Matches[1]
        }

        if ($taskId) {
            $taskFileName = "$taskId.md"
            $candidateTaskPaths = @(
                "docs/exec-plans/active/tasks/$taskFileName",
                "docs/exec-plans/completed/tasks/$taskFileName"
            )

            foreach ($candidateTaskPath in $candidateTaskPaths) {
                $taskAbsolute = Join-Path $repoRoot $candidateTaskPath
                if (-not (Test-Path -LiteralPath $taskAbsolute)) {
                    continue
                }

                $taskContent = [System.IO.File]::ReadAllText($taskAbsolute)
                $linkedTaskStatus = Get-TaskStatus -Content $taskContent
                if ($linkedTaskStatus -eq "COMPLETED") {
                    Add-Issue -Issues $issues -Message "active handoff '$handoffPath' points to completed task '$taskId' and should be archived under docs/handoff/completed/."
                }
                break
            }
        }
    }
}

if ($issues.Count -gt 0) {
    Write-Warning "task-handoff-check: mode=$mode"
    if ($AuditRepo) {
        Write-Warning "task-handoff-check: repository audit mode validates all tracked task and handoff artifacts."
    }
    else {
        Write-Warning "task-handoff-check: this check is currently intended to prevent silent drift in multi-agent execution."
    }
    if ($mode -eq "block") {
        exit 1
    }
}

exit 0
