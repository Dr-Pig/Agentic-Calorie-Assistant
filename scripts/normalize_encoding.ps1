param(
    [string]$Root = (Get-Location).Path,
    [switch]$DocsPolicy,
    [switch]$StagedOnly
)

$ErrorActionPreference = "Stop"

if ((@($DocsPolicy, $StagedOnly) | Where-Object { $_ }).Count -gt 1) {
    throw "Specify only one mode: -DocsPolicy or -StagedOnly."
}

if (-not $DocsPolicy -and -not $StagedOnly) {
    $DocsPolicy = $true
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

function Test-IsPolicyPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $normalized = $RelativePath.Replace('\', '/')

    if ($normalized -eq 'AGENTS.md') {
        return $true
    }

    if ($normalized.StartsWith('docs/archive/')) {
        return $false
    }

    if ($normalized.StartsWith('docs/') -and $normalized.EndsWith('.md')) {
        return $true
    }

    return $false
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

function Get-PolicyFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [switch]$OnlyStaged
    )

    if ($OnlyStaged) {
        $files = @()
        $stagedNames = git -C $RepoRoot diff --cached --name-only --diff-filter=AM
        foreach ($relative in $stagedNames) {
            if (-not (Test-IsPolicyPath -RelativePath $relative)) {
                continue
            }

            $fullPath = Join-Path $RepoRoot $relative
            if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
                $files += $fullPath
            }
        }

        return $files | Sort-Object -Unique
    }

    $docRoot = Join-Path $RepoRoot 'docs'
    $files = @()
    if (Test-Path -LiteralPath $docRoot -PathType Container) {
        $files += Get-ChildItem -Path $docRoot -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue |
            Where-Object { -not ((Get-RelativePathCompat -BasePath $RepoRoot -TargetPath $_.FullName).Replace('\', '/').StartsWith('docs/archive/')) } |
            ForEach-Object { $_.FullName }
    }

    $agentsPath = Join-Path $RepoRoot 'AGENTS.md'
    if (Test-Path -LiteralPath $agentsPath -PathType Leaf) {
        $files += $agentsPath
    }

    return $files | Sort-Object -Unique
}

$repoRoot = Get-RepoRoot -CandidateRoot $Root
$targets = Get-PolicyFiles -RepoRoot $repoRoot -OnlyStaged:$StagedOnly
$utf8Bom = New-Object System.Text.UTF8Encoding($true)
$rewritten = 0

foreach ($path in $targets) {
    $text = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
    [System.IO.File]::WriteAllText($path, $text, $utf8Bom)
    $rewritten += 1
    Write-Output "NORMALIZED $path"
}

Write-Output ""
Write-Output "Normalized files: $rewritten"
