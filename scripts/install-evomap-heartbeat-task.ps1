$ErrorActionPreference = "Stop"

$taskName = "Codex EvoMap Heartbeat"
$repoRoot = Split-Path -Parent $PSScriptRoot
$heartbeatScript = Join-Path $repoRoot "scripts\heartbeat-evomap.ps1"

if (-not (Test-Path $heartbeatScript)) {
  throw "Missing heartbeat script: $heartbeatScript"
}

$taskCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $heartbeatScript + '"'

& schtasks.exe /Create `
  /TN $taskName `
  /SC MINUTE `
  /MO 5 `
  /TR $taskCommand `
  /F | Out-Null

& schtasks.exe /Run /TN $taskName | Out-Null

Write-Output "Installed scheduled task: $taskName"
