param(
  [ValidateSet("desktop", "chat", "today", "body", "feedback", "review", "data")]
  [string]$Page = "desktop",
  [string]$UserId = "local-self-use-001",
  [string]$LocalDate = (Get-Date -Format "yyyy-MM-dd"),
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DataDir = Join-Path $RepoRoot "workspace_data\local_dogfood"
$TokenFile = Join-Path $DataDir "local_debug_token.txt"
$DbPath = "workspace_data/local_dogfood/accurate_intake.sqlite3"
$DescriptorPath = "artifacts/accurate_intake_desktop_dogfood_launcher.json"

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
if (-not (Test-Path -LiteralPath $TokenFile)) {
  $tokenValue = [guid]::NewGuid().ToString("N")
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($TokenFile, $tokenValue, $utf8NoBom)
}
$Token = (Get-Content -Raw -LiteralPath $TokenFile).Trim()
$pagePath = "accurate-intake-$Page.html"
$pageRoute = if ($Page -eq "desktop") { "accurate-intake" } else { "accurate-intake/$Page" }

function Test-AcaServer {
  try {
    $response = Invoke-RestMethod -Uri "http://$HostName`:$Port/ping" -TimeoutSec 2
    return $null -ne $response
  } catch {
    return $false
  }
}

function Test-AcaPage {
  try {
    $response = Invoke-WebRequest -Uri "http://$HostName`:$Port/static/$pagePath" -UseBasicParsing -TimeoutSec 2
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

function Test-AcaAutoSession {
  try {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $escapedUser = [uri]::EscapeDataString($UserId)
    Invoke-WebRequest `
      -Uri "http://$HostName`:$Port/accurate-intake?user_id=$escapedUser" `
      -WebSession $session `
      -UseBasicParsing `
      -TimeoutSec 2 | Out-Null
    $response = Invoke-WebRequest `
      -Uri "http://$HostName`:$Port/accurate-intake/local-debug-session" `
      -WebSession $session `
      -UseBasicParsing `
      -TimeoutSec 2
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

function Stop-AcaServerIfOwned {
  $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($listener in $listeners) {
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
    $commandLine = [string]$processInfo.CommandLine
    if ($commandLine -like "*run_accurate_intake_desktop_dogfood_launcher.py*") {
      Stop-Process -Id $listener.OwningProcess -Force
      return $true
    }
  }
  return $false
}

function Start-AcaServer {
  $command = "Set-Location -LiteralPath '$RepoRoot'; `$env:PYTHONUTF8='1'; python scripts/run_accurate_intake_desktop_dogfood_launcher.py --db-path '$DbPath' --local-debug-token '$Token' --port $Port --user-id '$UserId' --output '$DescriptorPath' --no-open-browser"
  Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
    -WindowStyle Hidden | Out-Null
}

if ((Test-AcaServer) -and (-not (Test-AcaPage))) {
  Write-Host "Accurate Intake server is responding, but /static/$pagePath is missing. Restarting the local ACA server."
  Stop-AcaServerIfOwned | Out-Null
  Start-Sleep -Milliseconds 750
}

if ((Test-AcaServer) -and (Test-AcaPage) -and (-not (Test-AcaAutoSession))) {
  Write-Host "Accurate Intake server is running without automatic local session support. Restarting the local ACA server."
  Stop-AcaServerIfOwned | Out-Null
  Start-Sleep -Milliseconds 750
}

if ((-not (Test-AcaServer)) -or (-not (Test-AcaPage))) {
  Start-AcaServer
  $ready = $false
  for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 750
    if ((Test-AcaServer) -and (Test-AcaPage)) {
      $ready = $true
      break
    }
  }
  if (-not $ready) {
    Write-Host "Accurate Intake server did not become ready for /static/$pagePath on http://$HostName`:$Port within 45 seconds."
    Write-Host "Token file: $TokenFile"
    exit 1
  }
}

$escapedUserForUrl = [uri]::EscapeDataString($UserId)
$url = "http://$HostName`:$Port/${pageRoute}?user_id=$escapedUserForUrl&local_date=$LocalDate"
Start-Process $url

Write-Host "Local debug session is established automatically through the ACA launcher route."
Write-Host "Manual fallback token file: $TokenFile"
