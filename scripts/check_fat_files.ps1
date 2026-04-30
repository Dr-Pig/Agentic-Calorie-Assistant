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
        [AllowEmptyString()]
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

    try {
        $result = & git show "HEAD:$Path" 2>$null
    }
    catch {
        return $null
    }

    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    return $result
}

function Get-StagedText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        $result = & git show ":$Path" 2>$null
    }
    catch {
        return $null
    }

    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    return $result
}

function Get-StagedPaths {
    $output = & git diff --cached --name-only --diff-filter=ACMR
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read staged paths."
    }

    return @($output | Where-Object { $_ -and $_.Trim().Length -gt 0 })
}

function Get-StagedDeletedPaths {
    $output = & git diff --cached --name-only --diff-filter=D
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read staged deleted paths."
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

function Get-ActiveCodePolicy {
    $policyPath = Join-Path $repoRoot "config/active_code_policy.jsonc"
    if (-not (Test-Path -LiteralPath $policyPath)) {
        throw "Unable to find active code policy at $policyPath"
    }

    return Get-Content -Encoding UTF8 -Raw -LiteralPath $policyPath | ConvertFrom-Json
}

function Get-NormalizedRepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return ($Path -replace "\\", "/")
}

function Test-RepoPathMatchesPattern {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Pattern
    )

    $normalizedPath = Get-NormalizedRepoPath -Path $Path
    $normalizedPattern = Get-NormalizedRepoPath -Path $Pattern
    return $normalizedPath -like $normalizedPattern
}

function Test-PolicyHasTransitionOverride {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Policy
    )

    if ($null -eq $Policy.transition_overrides) {
        return $false
    }

    $propertyNames = @($Policy.transition_overrides.PSObject.Properties | ForEach-Object { $_.Name })
    if ($propertyNames.Count -eq 0) {
        return $false
    }

    return $propertyNames -contains $Path
}

function Get-PolicyTransitionOverrideValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Policy
    )

    if (-not (Test-PolicyHasTransitionOverride -Path $Path -Policy $Policy)) {
        return $null
    }

    return [int]$Policy.transition_overrides.PSObject.Properties[$Path].Value
}

function Get-PolicyCategoryForPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Policy
    )

    foreach ($rule in $Policy.category_rules) {
        if (Test-RepoPathMatchesPattern -Path $Path -Pattern ([string]$rule.pattern)) {
            return [string]$rule.category
        }
    }

    return $null
}

function Get-PolicyTargetCapForPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Policy
    )

    $category = Get-PolicyCategoryForPath -Path $Path -Policy $Policy
    if ($null -eq $category) {
        return $null
    }

    return [int]$Policy.category_caps.PSObject.Properties[$category].Value
}

function Get-PolicyEffectiveCapForPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [object]$Policy
    )

    if (Test-PolicyHasTransitionOverride -Path $Path -Policy $Policy) {
        return Get-PolicyTransitionOverrideValue -Path $Path -Policy $Policy
    }

    return Get-PolicyTargetCapForPath -Path $Path -Policy $Policy
}

function Get-ActivePythonPolicyRows {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Policy
    )

    $rows = New-Object System.Collections.Generic.List[hashtable]
    $appRoot = Join-Path $repoRoot ([string]$Policy.active_code.root)
    $excludedPatterns = @()
    foreach ($pattern in $Policy.active_code.excluded_globs) {
        $excludedPatterns += [string]$pattern
    }

    $files = Get-ChildItem -Path $appRoot -Recurse -Filter *.py -File
    foreach ($file in $files) {
        $fullPath = $file.FullName
        $rootWithSeparator = $repoRoot.Path.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        if ($fullPath.StartsWith($rootWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)) {
            $relativePath = $fullPath.Substring($rootWithSeparator.Length)
        }
        else {
            $relativePath = $fullPath
        }
        $normalizedPath = Get-NormalizedRepoPath -Path $relativePath
        $isExcluded = $false
        foreach ($pattern in $excludedPatterns) {
            if (Test-RepoPathMatchesPattern -Path $normalizedPath -Pattern $pattern) {
                $isExcluded = $true
                break
            }
        }
        if ($isExcluded) {
            continue
        }

        $rows.Add(@{
            Path = $normalizedPath
            Category = Get-PolicyCategoryForPath -Path $normalizedPath -Policy $Policy
            TargetCap = Get-PolicyTargetCapForPath -Path $normalizedPath -Policy $Policy
            EffectiveCap = Get-PolicyEffectiveCapForPath -Path $normalizedPath -Policy $Policy
            UsesTransitionOverride = (Test-PolicyHasTransitionOverride -Path $normalizedPath -Policy $Policy)
        })
    }

    return @($rows)
}

function Test-FreezeGrowthJustification {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
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

    $structuralExemptPaths = @(
        "app/providers/builderspace_adapter.py",
        "app/providers/deepseek_adapter.py",
        "app/runtime/agent/manager_branch_contract.py",
        "app/intake/application/intake_turn_orchestrator.py",
        "app/intake/application/intake_execution_orchestrator.py"
    )
    if ($structuralExemptPaths -contains $Path) {
        return $violations
    }

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
$activeCodePolicy = Get-ActiveCodePolicy
$activePythonPolicyRows = @(Get-ActivePythonPolicyRows -Policy $activeCodePolicy)

$protectedRules = @(
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
    },
    @{
        Path = "app/runtime/application/manager_service.py"
        Threshold = 500
        Kind = "runtime-manager"
        Rule = "protected: single manager service must stay bounded; extract domain logic to business-domain application services"
    },
    @{
        Path = "app/intake/application/intake_turn_orchestrator.py"
        Threshold = 360
        Kind = "application-service"
        Rule = "protected: Wave 1 intake turn orchestration must stay bounded; delegate domain logic and persistence details"
    },
    @{
        Path = "app/intake/application/intake_execution_orchestrator.py"
        Threshold = 360
        Kind = "application-service"
        Rule = "protected: Wave 1 execution orchestration must stay thin; delegate tool execution and persistence seams"
    },
    @{
        Path = "app/providers/builderspace_adapter.py"
        Threshold = 1100
        Kind = "provider-adapter"
        Rule = "protected: BuilderSpace transport work is temporarily ceiling-managed until extraction work lands"
    },
    @{
        Path = "app/providers/deepseek_adapter.py"
        Threshold = 500
        Kind = "provider-adapter"
        Rule = "protected: DeepSeek transport work is temporarily ceiling-managed until extraction work lands"
    },
    @{
        Path = "app/runtime/agent/manager_branch_contract.py"
        Threshold = 550
        Kind = "runtime-contract"
        Rule = "protected: shared manager branch contract helpers are temporarily ceiling-managed until further extraction work lands"
    }
)

$freezeGrowthRules = @()

$watchlistRules = @(
    @{
        Path = "app/nutrition/agent/nutrition_profiles.py"
        WatchLines = 170
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/nutrition_lookup_policy.py"
        WatchLines = 280
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/nutrition_estimation_support.py"
        WatchLines = 160
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/risk_gate_policy.py"
        WatchLines = 140
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/nutrition_engine.py"
        WatchLines = 50
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/exact_item_packets.py"
        WatchLines = 90
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/knowledge_lookup_normalizer.py"
        WatchLines = 120
        Kind = "nutrition-agent-watchlist"
    },
    @{
        Path = "app/nutrition/agent/knowledge_loader.py"
        WatchLines = 60
        Kind = "nutrition-agent-watchlist"
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
    Write-Output "Active code policy audit:"

    foreach ($row in $activePythonPolicyRows) {
        $path = [string]$row.Path
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }

        $text = Get-Content -Encoding UTF8 -Raw -LiteralPath $path
        $lines = Get-LineCountFromText -Text $text
        $category = [string]$row.Category
        $targetCap = $row.TargetCap
        $effectiveCap = $row.EffectiveCap
        $usesTransitionOverride = [bool]$row.UsesTransitionOverride

        if ([string]::IsNullOrWhiteSpace($category)) {
            Write-Output ("[UNMAPPED] {0} lines={1}" -f $path, $lines)
            $warnings.Add("$path is not mapped to an active code category")
            continue
        }

        if ($lines -gt $targetCap) {
            $targetStatus = "TARGET_OVER"
            $warnings.Add("$path is above target cap ($lines > $targetCap) for category $category")
        }
        elseif ($lines -eq $targetCap) {
            $targetStatus = "TARGET_EDGE"
        }
        else {
            $targetStatus = "TARGET_OK"
        }

        Write-Output ("[{0}] {1} lines={2} category={3} target={4} effective={5} transition_override={6}" -f $targetStatus, $path, $lines, $category, $targetCap, $effectiveCap, $usesTransitionOverride.ToString().ToLowerInvariant())

        if ($lines -gt $effectiveCap) {
            $warnings.Add("$path exceeded effective transition cap ($lines > $effectiveCap)")
        }
    }

    Write-Output ""
    Write-Output "Guidance:"
    Write-Output "- protected files above threshold should only shrink or stay flat during extraction work"
    Write-Output "- freeze-growth files must not grow until an extraction task reduces their responsibility pressure"
    Write-Output "- watchlist files need boundary review before they join the freeze-growth set"
    Write-Output "- new responsibilities should move into application/domain/support modules"
    Write-Output "- files above target caps may exist temporarily under transition overrides, but they must not continue growing"
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
    $stagedDeletedPathSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($deletedPath in (Get-StagedDeletedPaths)) {
        [void]$stagedDeletedPathSet.Add($deletedPath)
    }
    $governanceTexts = @(Get-StagedGovernanceTexts)

    foreach ($path in $stagedPaths) {
        $isProtected = $protectedMap.ContainsKey($path)
        $isFrozen = $freezeMap.ContainsKey($path)
        $policyCategory = Get-PolicyCategoryForPath -Path $path -Policy $activeCodePolicy
        $policyTargetCap = Get-PolicyTargetCapForPath -Path $path -Policy $activeCodePolicy
        $policyEffectiveCap = Get-PolicyEffectiveCapForPath -Path $path -Policy $activeCodePolicy
        $usesTransitionOverride = Test-PolicyHasTransitionOverride -Path $path -Policy $activeCodePolicy

        if (-not $isProtected -and -not $isFrozen) {
            $isActivePython = $path.StartsWith("app/", [System.StringComparison]::OrdinalIgnoreCase) -and
                              $path.EndsWith(".py", [System.StringComparison]::OrdinalIgnoreCase)

            if ($isActivePython) {
                $stagedBlobForPolicy = Get-StagedText -Path $path
                if ($null -eq $stagedBlobForPolicy) {
                    continue
                }

                $headTextForPolicy = Get-HeadText -Path $path
                $headLinesForPolicy = if ($null -eq $headTextForPolicy) { 0 } else { Get-LineCountFromText -Text ($headTextForPolicy -join "`n") }
                $stagedLinesForPolicy = Get-LineCountFromText -Text ($stagedBlobForPolicy -join "`n")

                if ($null -eq $policyCategory) {
                    $violations.Add("$path is an active Python module but is not mapped to any active code category.")
                    continue
                }

                if ($headLinesForPolicy -eq 0 -and $stagedLinesForPolicy -gt [int]$activeCodePolicy.active_code.new_active_python_file_default_cap) {
                    $violations.Add("$path is a new active Python module and exceeded the new-file cap ($stagedLinesForPolicy > $($activeCodePolicy.active_code.new_active_python_file_default_cap)).")
                    continue
                }

                if ($headLinesForPolicy -gt $policyTargetCap -and $stagedLinesForPolicy -gt $headLinesForPolicy) {
                    $violations.Add("$path grew from $headLinesForPolicy to $stagedLinesForPolicy while already above its target cap $policyTargetCap for category $policyCategory.")
                    continue
                }

                if ($headLinesForPolicy -le $policyEffectiveCap -and $stagedLinesForPolicy -gt $policyEffectiveCap) {
                    $violations.Add("$path crossed its effective cap $policyEffectiveCap for category $policyCategory ($headLinesForPolicy -> $stagedLinesForPolicy).")
                    continue
                }

                if ($usesTransitionOverride -and $stagedLinesForPolicy -eq $headLinesForPolicy -and $headLinesForPolicy -gt $policyTargetCap) {
                    $warnings.Add("$path remains above target cap $policyTargetCap under a transition override; prefer shrink-only follow-up.")
                }
            }

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
            $legacyDeleted = $false
            if ($rule.ContainsKey("LegacyPath")) {
                $legacyDeleted = $stagedDeletedPathSet.Contains([string]$rule.LegacyPath)
            }

            if ($stagedLines -gt $rule.FreezeLines) {
                $violations.Add("$path exceeded freeze-growth ceiling $($rule.FreezeLines) ($headLines -> $stagedLines)")
                continue
            }

            if ($stagedLines -gt $headLines -and -not ($headLines -eq 0 -and $legacyDeleted)) {
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
