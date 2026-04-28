# Runtime UI - One Click Launcher
# This script checks if the server is running and opens the root UI in your default browser.

$port = 8011
$url = "http://127.0.0.1:$port/"

# Check if the port is active
$activePort = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

if ($activePort) {
    Write-Host "[SYSTEM] Server is already running. Opening UI..." -ForegroundColor Green
    Start-Process $url
} else {
    Write-Host "[SYSTEM] Server is NOT running. Attempting to start..." -ForegroundColor Yellow
    Write-Host "[SYSTEM] Running: python -m uvicorn app.main:app --host 127.0.0.1 --port $port" -ForegroundColor Gray
    
    # Start the server in a new window so it remains running
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn app.main:app --host 127.0.0.1 --port $port"
    
    # Wait for startup
    Write-Host "[SYSTEM] Waiting for server startup (3 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
    
    # Open UI
    Start-Process $url
}
