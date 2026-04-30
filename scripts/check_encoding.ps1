param(
    [string]$Root = (Get-Location).Path,
    [switch]$AuditDocsPolicy,
    [switch]$StagedOnly,
    [switch]$AuditAll
)

$ErrorActionPreference = "Stop"

if ((@($AuditDocsPolicy, $StagedOnly, $AuditAll) | Where-Object { $_ }).Count -gt 1) {
    throw "Specify only one mode: -AuditDocsPolicy, -StagedOnly, or -AuditAll."
}

if (-not $AuditDocsPolicy -and -not $StagedOnly -and -not $AuditAll) {
    $AuditDocsPolicy = $true
}

function Get-EncodingStatus {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $bytes = [System.IO.File]::ReadAllBytes($Path)

    if ($bytes.Length -ge 3 -and
        $bytes[0] -eq 0xEF -and
        $bytes[1] -eq 0xBB -and
        $bytes[2] -eq 0xBF) {
        return "UTF8-BOM"
    }

    if ($bytes.Length -ge 2 -and
        $bytes[0] -eq 0xFF -and
        $bytes[1] -eq 0xFE) {
        return "UTF16-LE"
    }

    if ($bytes.Length -ge 2 -and
        $bytes[0] -eq 0xFE -and
        $bytes[1] -eq 0xFF) {
        return "UTF16-BE"
    }

    try {
        $null = [System.Text.UTF8Encoding]::new($false, $true).GetString($bytes)
        return "UTF8-NO-BOM"
    } catch {
        return "UNKNOWN-NONUTF8"
    }
}

function Test-IsPolicyPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $normalized = $RelativePath.Replace('\', '/')

    if ($normalized -eq 'AGENTS.md') {
        return $true
    }

    if ($normalized.StartsWith('docs/') -and $normalized.EndsWith('.md')) {
        return $true
    }

    return $false
}

function Get-RepoRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CandidateRoot
    )

    $resolvedRoot = (Resolve-Path -LiteralPath $CandidateRoot).Path
    try {
        $gitRoot = git -C $resolvedRoot rev-parse --show-toplevel 2>$null
        if ($LASTEXITCODE -eq 0 -and $gitRoot) {
            return $gitRoot.Trim()
        }
    } catch {
    }

    return $resolvedRoot
}

function Get-RelativePathCompat {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    $baseUri = [System.Uri]((Resolve-Path -LiteralPath $BasePath).Path.TrimEnd('\') + '\')
    $targetUri = [System.Uri]((Resolve-Path -LiteralPath $TargetPath).Path)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace('/', '\')
}

function New-Result {
    param(
        [string]$Status,
        [string]$Path,
        [bool]$InPolicyScope
    )

    [PSCustomObject]@{
        Status = $Status
        Path = $Path
        InPolicyScope = $InPolicyScope
    }
}

$repoRoot = Get-RepoRoot -CandidateRoot $Root
$results = @()

if ($StagedOnly) {
    $stagedNames = git -C $repoRoot diff --cached --name-only --diff-filter=AM
    foreach ($relative in $stagedNames) {
        if (-not (Test-IsPolicyPath -RelativePath $relative)) {
            continue
        }

        $fullPath = Join-Path $repoRoot $relative
        if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
            continue
        }

        $status = Get-EncodingStatus -Path $fullPath
        $results += New-Result -Status $status -Path $fullPath -InPolicyScope $true
    }
}
elseif ($AuditDocsPolicy) {
    $docRoot = Join-Path $repoRoot 'docs'
    $docFiles = @()
    if (Test-Path -LiteralPath $docRoot -PathType Container) {
        $docFiles = Get-ChildItem -Path $docRoot -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue
    }

    $allFiles = @($docFiles)
    $agentsPath = Join-Path $repoRoot 'AGENTS.md'
    if (Test-Path -LiteralPath $agentsPath -PathType Leaf) {
        $allFiles += Get-Item -LiteralPath $agentsPath
    }

    foreach ($file in $allFiles) {
        $status = Get-EncodingStatus -Path $file.FullName
        $results += New-Result -Status $status -Path $file.FullName -InPolicyScope $true
    }
}
elseif ($AuditAll) {
    $files = Get-ChildItem -Path $repoRoot -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $relative = [System.IO.Path]::GetRelativePath($repoRoot, $file.FullName)
        $status = Get-EncodingStatus -Path $file.FullName
        $results += New-Result -Status $status -Path $file.FullName -InPolicyScope (Test-IsPolicyPath -RelativePath $relative)
    }
}

$badPolicy = $results | Where-Object { $_.InPolicyScope -and $_.Status -ne 'UTF8-BOM' }
$badNonPolicy = $results | Where-Object { -not $_.InPolicyScope -and $_.Status -ne 'UTF8-BOM' }

Write-Output "Encoding check root: $repoRoot"
Write-Output ""

if ($AuditDocsPolicy) {
    Write-Output "Mode: AuditDocsPolicy (`docs/**/*.md` + `AGENTS.md`)"
    Write-Output ""
}
elseif ($StagedOnly) {
    Write-Output "Mode: StagedOnly (policy-scoped markdown only)"
    Write-Output ""
}
else {
    Write-Output "Mode: AuditAll (all repo markdown; policy scope flagged separately)"
    Write-Output ""
}

if ($badPolicy.Count -eq 0 -and (-not $AuditAll -or $badNonPolicy.Count -eq 0)) {
    Write-Output "All checked files passed for the selected mode."
    exit 0
}

if ($badPolicy.Count -gt 0) {
    Write-Output "Policy-scope violations:"
    $badPolicy | Sort-Object Status, Path | Format-Table -AutoSize | Out-String | Write-Output
}

if ($AuditAll -and $badNonPolicy.Count -gt 0) {
    Write-Output "Non-policy markdown findings:"
    $badNonPolicy | Sort-Object Status, Path | Format-Table -AutoSize | Out-String | Write-Output
}

if ($badPolicy.Count -gt 0) {
    exit 1
}

exit 0
