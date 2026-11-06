# ONLINE mode with the local Anthill imitation (tools/mock-backend).
# Starts the back-end (if it is not running) and the client. The client goes the normal way:
# main menu -> hub (lobby) -> matches; the back-end starts game servers on demand (build\rooms\*.log).
# Usage: play-online.bat [nickname]
# Friends connect with connect-online.bat to the address printed below (Radmin VPN is detected).
param([string]$Name = $env:USERNAME)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$java = 'java'
if (Test-Path 'C:\Program Files\Java\jdk-17\bin\java.exe') { $java = 'C:\Program Files\Java\jdk-17\bin\java.exe' }
$py = Join-Path $root 'build\pyenv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
$port = 9511

# address friends use: BRAINOUT_PUBLIC_HOST, else the Radmin VPN address (26.x.x.x), else localhost
$public = $env:BRAINOUT_PUBLIC_HOST
if (-not $public) {
    $radmin = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -like '26.*' } | Select-Object -First 1
    $public = if ($radmin) { $radmin.IPAddress } else { '127.0.0.1' }
}
$base = "http://${public}:$port"
New-Item -ItemType Directory -Force (Join-Path $root 'build') | Out-Null

function Test-Backend { try { Invoke-RestMethod "http://127.0.0.1:$port/discovery/services/login" -TimeoutSec 2 | Out-Null; $true } catch { $false } }

if (-not (Test-Backend)) {
    Write-Host "Starting back-end, friends connect to: $public"
    Start-Process -FilePath $py -ArgumentList '-u', "`"$root\tools\mock-backend\backend.py`"", '--port', $port, '--public-host', $public `
        -WorkingDirectory $root -WindowStyle Minimized -RedirectStandardOutput "$root\build\backend-out.log" -RedirectStandardError "$root\build\backend-err.log"
    for ($i = 0; $i -lt 20 -and -not (Test-Backend); $i++) { Start-Sleep 1 }
    if (-not (Test-Backend)) { Write-Host 'Back-end did not start, see build\backend-err.log'; Read-Host 'Press Enter'; exit 1 }
}

$cargs = @('-jar', 'brainout-desktop.jar', '--unsafe', '--env', "$base/environment")
if ($Name) { $cargs += @('--name', $Name) }
# own online account per nickname (the game keeps accounts per DESKTOP_PROFILE_NAME)
if ($Name) { $env:DESKTOP_PROFILE_NAME = $Name }
Start-Process -FilePath $java -WorkingDirectory "$root\bin\client" -ArgumentList $cargs `
    -RedirectStandardOutput "$root\build\client-last.log" -RedirectStandardError "$root\build\client-last.err"
Write-Host "Online: friends run connect-online.bat and enter $public"
