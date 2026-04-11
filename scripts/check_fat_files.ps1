param(
    [switch]$StagedOnly,
    [switch]$AuditAll,
    [switch]$NoFailOnWarnings
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-LineCountFromText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    if ($Text.Length -eq 0) {
        return 0
    }

    $normalized = $Text -replace "`r`n", "`n"
    return ($normalized.Split("`n")).Count
}

function Get-HeadText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    & git show "HEAD:$Path" 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
}

function Get-StagedText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    & git show ":$Path" 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
}

function Get-StagedPaths {
    $output = & git diff --cached --name-only --diff-filter=ACMR
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read staged paths."
    }

    return @($output | Where-Object { $_ -and $_.Trim().Length -gt 0 })
}

function Get-StagedGovernanceTexts {
    $governancePaths = @()
    $stagedPaths = Get-StagedPaths
    foreach ($path in $stagedPaths) {
        if (
            $path.StartsWith("docs/exec-plans/active/tasks/", [System.StringComparison]::OrdinalIgnoreCase) -or
            $path.StartsWith("docs/exec-plans/completed/tasks/", [System.StringComparison]::OrdinalIgnoreCase) -or
            $path.Equals("docs/exec-plans/active/REPLAN_LOG.md", [System.StringComparison]::OrdinalIgnoreCase)
        ) {
            $governancePaths += $path
        }
    }

    $texts = New-Object System.Collections.Generic.List[string]
    foreach ($path in $governancePaths) {
        $text = Get-StagedText -Path $path
        if ($null -ne $text) {
            $texts.Add(($text -join "`n"))
        }
    }

    return @($texts)
}

function Test-FreezeGrowthJustification {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string[]]$GovernanceTexts
    )

    if ($GovernanceTexts.Count -eq 0) {
        return $false
    }

    $pathPattern = [Regex]::Escape($Path)
    $reasonPatterns = @(
        'shrink-only extraction',
        'contained bug fix',
        'boundary-safe wiring',
        'pure wiring / compatibility',
        'pure wiring',
        'compatibility shim'
    )

    foreach ($text in $GovernanceTexts) {
        if ($text -match $pathPattern) {
            foreach ($reason in $reasonPatterns) {
                if ($text -match [Regex]::Escape($reason)) {
                    return $true
                }
            }
        }
    }

    return $false
}

function Get-StructuralViolations {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $violations = [System.Collections.Generic.List[string]]::new()
    $normalized = $Text -replace "`r`n", "`n"

    $commonDisallowed = @(
        '(?m)^\s*async\s+def\b',
        '(?m)^\s*def\b',
        '(?m)^\s*class\b'
    )
    foreach ($pattern in $commonDisallowed) {
        if ($normalized -match $pattern) {
            $violations.Add("contains executable definitions")
            break
        }
    }

    switch ($Path) {
        "app/usecases/text_meal.py" {
            $patterns = @(
                '(?m)^\s*(if|for|while|try|with)\b',
                '(?m)^\s*return\b',
                '(?m)^\s*await\b'
            )
            foreach ($pattern in $patterns) {
                if ($normalized -match $pattern) {
                    $violations.Add("must remain an import-and-re-export compatibility shim")
                    break
                }
            }
        }
        "app/schemas.py" {
            $patterns = @(
                '(?m)^\s*(if|for|while|try|with)\b',
                '(?m)^\s*return\b',
                '(?m)^\s*@'
            )
            foreach ($pattern in $patterns) {
                if ($normalized -match $pattern) {
                    $violations.Add("must remain an import-and-re-export schema surface")
                    break
                }
            }
        }
        "app/routes.py" {
            $patterns = @(
                '(?m)^\s*@\w+',
                'router\.(get|post|put|patch|delete|websocket)\(',
                '(?m)^\s*(if|for|while|try|with)\b',
                '(?m)^\s*return\b'
            )
            foreach ($pattern in $patterns) {
                if ($normalized -match $pattern) {
                    $violations.Add("must remain a thin router assembly surface")
                    break
                }
            }
        }
    }

    return $violations
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$protectedRules = @(
    @{
        Path = "app/usecases/text_meal.py"
        Threshold = 350
        Kind = "entrypoint"
        Rule = "protected: must not grow while above threshold"
    },
    @{
        Path = "app/schemas.py"
        Threshold = 450
        Kind = "schema"
        Rule = "protected: new contracts must move into workflow-specific schema files"
    },
    @{
        Path = "app/routes.py"
        Threshold = 400
        Kind = "routes"
        Rule = "protected: new surfaces should prefer dedicated route modules or adapters"
    }
)

$freezeGrowthRules = @(
    @{
        Path = "app/application/evidence_assembly.py"
        FreezeLines = 962
        Kind = "application-freeze"
    },
    @{
        Path = "app/application/context_assembly.py"
        FreezeLines = 636
        Kind = "application-freeze"
    },
    @{
        Path = "app/agent/knowledge_packets.py"
        FreezeLines = 1058
        Kind = "agent-freeze"
    }
)

$watchlistRules = @(
    @{
        Path = "app/agent/nutrition_engine.py"
        WatchLines = 571
        Kind = "agent-watchlist"
    }
)

$violations = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

if (-not $StagedOnly -and -not $AuditAll) {
    $AuditAll = $true
}

if ($AuditAll) {
    Write-Output "Fat-file audit (workspace)"
    Write-Output ""

    foreach ($rule in $protectedRules) {
        $path = $rule.Path
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }

        $text = Get-Content -Encoding UTF8 -Raw -LiteralPath $path
        $lines = Get-LineCountFromText -Text $text
        $status = if ($lines -gt $rule.Threshold) { "OVER" } else { "OK" }
        Write-Output ("[{0}] {1} lines={2} threshold={3} kind={4}" -f $status, $path, $lines, $rule.Threshold, $rule.Kind)
        if ($status -eq "OVER") {
            $warnings.Add("$path is above protected threshold ($lines > $($rule.Threshold))")
        }

        $structureViolations = @(Get-StructuralViolations -Path $path -Text $text)
        if ($structureViolations.Count -eq 0) {
            Write-Output ("[OK] {0} structure=thin-{1}" -f $path, $rule.Kind)
        }
        else {
            foreach ($structureViolation in $structureViolations) {
                Write-Output ("[DRIFT] {0} structure={1}" -f $path, $structureViolation)
                $warnings.Add("$path structural drift: $structureViolation")
            }
        }
    }

    foreach ($rule in $freezeGrowthRules) {
        $path = $rule.Path
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }

        $text = Get-Content -Encoding UTF8 -Raw -LiteralPath $path
        $lines = Get-LineCountFromText -Text $text
        $status = if ($lines -gt $rule.FreezeLines) { "OVER" } elseif ($lines -eq $rule.FreezeLines) { "FROZEN" } else { "SHRUNK" }
        Write-Output ("[{0}] {1} lines={2} freeze={3} kind={4}" -f $status, $path, $lines, $rule.FreezeLines, $rule.Kind)
        if ($lines -gt $rule.FreezeLines) {
            $warnings.Add("$path exceeded freeze-growth ceiling ($lines > $($rule.FreezeLines))")
        }
    }

    foreach ($rule in $watchlistRules) {
        $path = $rule.Path
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }

        $text = Get-Content -Encoding UTF8 -Raw -LiteralPath $path
        $lines = Get-LineCountFromText -Text $text
        $status = if ($lines -gt $rule.WatchLines) { "OVER" } elseif ($lines -eq $rule.WatchLines) { "WATCH" } else { "UNDER" }
        Write-Output ("[{0}] {1} lines={2} watch={3} kind={4}" -f $status, $path, $lines, $rule.WatchLines, $rule.Kind)
        if ($lines -gt $rule.WatchLines) {
            $warnings.Add("$path exceeded watchlist baseline ($lines > $($rule.WatchLines))")
        }
    }

    Write-Output ""
    Write-Output "Guidance:"
    Write-Output "- protected files above threshold should only shrink or stay flat during extraction work"
    Write-Output "- freeze-growth files must not grow until an extraction task reduces their responsibility pressure"
    Write-Output "- watchlist files need boundary review before they join the freeze-growth set"
    Write-Output "- new responsibilities should move into application/domain/support modules"
}

if ($StagedOnly) {
    Write-Output "Fat-file gate (staged changes)"
    Write-Output ""

    $stagedPaths = Get-StagedPaths
    $protectedMap = @{}
    foreach ($rule in $protectedRules) {
        $protectedMap[$rule.Path] = $rule
    }
    $freezeMap = @{}
    foreach ($rule in $freezeGrowthRules) {
        $freezeMap[$rule.Path] = $rule
    }
    $governanceTexts = @(Get-StagedGovernanceTexts)

    foreach ($path in $stagedPaths) {
        $isProtected = $protectedMap.ContainsKey($path)
        $isFrozen = $freezeMap.ContainsKey($path)

        if (-not $isProtected -and -not $isFrozen) {
            continue
        }

        $stagedText = Get-StagedText -Path $path
        if ($null -eq $stagedText) {
            continue
        }

        $headText = Get-HeadText -Path $path
        $headLines = if ($null -eq $headText) { 0 } else { Get-LineCountFromText -Text ($headText -join "`n") }
        $stagedLines = Get-LineCountFromText -Text ($stagedText -join "`n")
        $stagedBlob = ($stagedText -join "`n")

        if ($isProtected) {
            $rule = $protectedMap[$path]
            Write-Output ("- {0}: HEAD={1}, STAGED={2}, THRESHOLD={3}" -f $path, $headLines, $stagedLines, $rule.Threshold)

            if ($headLines -gt $rule.Threshold -and $stagedLines -gt $headLines) {
                $violations.Add("$path grew from $headLines to $stagedLines while already above the protected threshold $($rule.Threshold)")
                continue
            }

            if ($headLines -le $rule.Threshold -and $stagedLines -gt $rule.Threshold) {
                $violations.Add("$path crossed the protected threshold $($rule.Threshold) ($headLines -> $stagedLines)")
                continue
            }

            if ($headLines -gt $rule.Threshold -and $stagedLines -eq $headLines) {
                $warnings.Add("$path is still above threshold and was touched without shrinking; prefer extraction-first follow-up")
            }

            $structureViolations = @(Get-StructuralViolations -Path $path -Text $stagedBlob)
            foreach ($structureViolation in $structureViolations) {
                $violations.Add("$path structural violation: $structureViolation")
            }
        }

        if ($isFrozen) {
            $rule = $freezeMap[$path]
            Write-Output ("- {0}: HEAD={1}, STAGED={2}, FREEZE={3}" -f $path, $headLines, $stagedLines, $rule.FreezeLines)

            if ($stagedLines -gt $rule.FreezeLines) {
                $violations.Add("$path exceeded freeze-growth ceiling $($rule.FreezeLines) ($headLines -> $stagedLines)")
                continue
            }

            if ($stagedLines -gt $headLines) {
                $violations.Add("$path grew from $headLines to $stagedLines while in freeze-growth mode")
                continue
            }

            if (-not (Test-FreezeGrowthJustification -Path $path -GovernanceTexts $governanceTexts)) {
                $violations.Add("$path was touched in freeze-growth mode without a staged task artifact or re-plan note naming the file and classifying the change as shrink-only extraction, contained bug fix, or boundary-safe wiring")
                continue
            }

            if ($stagedLines -eq $headLines) {
                $warnings.Add("$path is in freeze-growth mode and was touched without shrinking; prefer extraction-first follow-up")
            }
        }
    }
}

if ($warnings.Count -gt 0) {
    Write-Output ""
    Write-Output "Warnings:"
    foreach ($warning in $warnings) {
        Write-Output ("- " + $warning)
    }
}

if ($violations.Count -gt 0) {
    Write-Output ""
    Write-Output "Violations:"
    foreach ($violation in $violations) {
        Write-Output ("- " + $violation)
    }

    Write-Output ""
    Write-Output "Blocked by fat-file gate."
    Write-Output "If the change is true boundary-consolidation work, record the reason in the active plan/replan log before retrying."
    exit 1
}

if ($warnings.Count -gt 0 -and -not $NoFailOnWarnings -and $StagedOnly) {
    exit 0
}

Write-Output ""
Write-Output "Fat-file check passed."
