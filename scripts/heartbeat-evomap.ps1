$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$configPath = "C:\Users\User\.codex\evomap-node.json"

if (-not (Test-Path $configPath)) {
  throw "Missing EvoMap config: $configPath"
}

$config = Get-Content -Raw $configPath | ConvertFrom-Json
$tmpBody = Join-Path $env:TEMP "evomap-heartbeat-body.json"
$body = @{ node_id = $config.node_id } | ConvertTo-Json -Compress
$body | Set-Content -LiteralPath $tmpBody -Encoding utf8

try {
  $originalHttpProxy = $env:HTTP_PROXY
  $originalHttpsProxy = $env:HTTPS_PROXY
  $originalAllProxy = $env:ALL_PROXY
  $originalNoProxy = $env:NO_PROXY
  $env:HTTP_PROXY = ""
  $env:HTTPS_PROXY = ""
  $env:ALL_PROXY = ""
  $env:NO_PROXY = "evomap.ai,localhost,127.0.0.1"

  try {
    $rawResponse = & curl.exe -sS `
      --noproxy "evomap.ai,localhost,127.0.0.1" `
      -X POST `
      "$($config.hub_url)/a2a/heartbeat" `
      -H "Content-Type: application/json" `
      -H "Authorization: Bearer $($config.node_secret)" `
      --data-binary "@$tmpBody"
  }
  finally {
    $env:HTTP_PROXY = $originalHttpProxy
    $env:HTTPS_PROXY = $originalHttpsProxy
    $env:ALL_PROXY = $originalAllProxy
    $env:NO_PROXY = $originalNoProxy
  }

  if ($LASTEXITCODE -ne 0) {
    throw "curl exited with code $LASTEXITCODE"
  }

  $response = $rawResponse | ConvertFrom-Json
}
finally {
  if (Test-Path $tmpBody) {
    Remove-Item -LiteralPath $tmpBody -Force -ErrorAction SilentlyContinue
  }
}

$config.last_heartbeat_at = [DateTime]::UtcNow.ToString("o")
if ($null -ne $response.claimed) {
  $config.claimed = [bool]$response.claimed
}
if ($response.next_heartbeat_ms) {
  $config.heartbeat_interval_ms = [int]$response.next_heartbeat_ms
}

$config | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $configPath
$response | ConvertTo-Json -Depth 20
