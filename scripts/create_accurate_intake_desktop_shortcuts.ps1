param(
  [string]$OutputDir = (Join-Path ([Environment]::GetFolderPath("Desktop")) "Accurate Intake ACA"),
  [string]$UserId = "local-self-use-001",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OpenScript = Join-Path $RepoRoot "scripts\open_accurate_intake_desktop_page.ps1"
$DataDir = Join-Path $RepoRoot "workspace_data\local_dogfood"
$TokenFile = Join-Path $DataDir "local_debug_token.txt"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
if (-not (Test-Path -LiteralPath $TokenFile)) {
  $tokenValue = [guid]::NewGuid().ToString("N")
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($TokenFile, $tokenValue, $utf8NoBom)
}

$Shell = New-Object -ComObject WScript.Shell

function New-AcaShortcut {
  param(
    [string]$Name,
    [string]$Page
  )
  $shortcut = $Shell.CreateShortcut((Join-Path $OutputDir $Name))
  $shortcut.TargetPath = "powershell.exe"
  $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$OpenScript`" -Page $Page -UserId `"$UserId`" -HostName `"$HostName`" -Port $Port"
  $shortcut.WorkingDirectory = $RepoRoot
  $shortcut.Description = "Open Accurate Intake $Page through the local friendly launcher route."
  $shortcut.Save()
}

$tokenShortcut = $Shell.CreateShortcut((Join-Path $OutputDir "ACA 0 Local Token.lnk"))
$tokenShortcut.TargetPath = "notepad.exe"
$tokenShortcut.Arguments = "`"$TokenFile`""
$tokenShortcut.WorkingDirectory = $RepoRoot
$tokenShortcut.Description = "Open the local debug token fallback file. Daily use should go through ACA 1 Start Home."
$tokenShortcut.Save()

New-AcaShortcut -Name "ACA 1 Start Home.lnk" -Page "desktop"
New-AcaShortcut -Name "ACA 2 Chat.lnk" -Page "chat"
New-AcaShortcut -Name "ACA 3 Today UI.lnk" -Page "today"
New-AcaShortcut -Name "ACA 4 Body.lnk" -Page "body"
New-AcaShortcut -Name "ACA 5 Feedback.lnk" -Page "feedback"
New-AcaShortcut -Name "ACA 6 Review.lnk" -Page "review"
New-AcaShortcut -Name "ACA 7 Data Backup Export.lnk" -Page "data"

Write-Host "Accurate Intake shortcuts created in: $OutputDir"
Write-Host "Open ACA 1 Start Home first to establish the local session cookie."
Write-Host "Manual fallback token file: $TokenFile"
