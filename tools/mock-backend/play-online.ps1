# ONLINE mode with the local Anthill imitation (tools/mock-backend).
# Starts the back-end (if it is not running) and the client. The client goes the normal way:
# main menu -> hub (lobby) -> matches; the back-end starts game servers on demand (build\rooms\*.log).
# Usage: play-online.bat
#        $env:BRAINOUT_PUBLIC_HOST = Radmin/LAN IP to let friends use this back-end
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$java = 'java'
if (Test-Path 'C:\Program Files\Java\jdk-17\bin\java.exe') { $java = 'C:\Program Files\Java\jdk-17\bin\java.exe' }
$py = Join-Path $root 'build\pyenv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
$port = 9511
$public = if ($env:BRAINOUT_PUBLIC_HOST) { $env:BRAINOUT_PUBLIC_HOST } else { '127.0.0.1' }
$base = "http://${public}:$port"
New-Item -ItemType Directory -Force (Join-Path $root 'build') | Out-Null

function Test-Backend { try { Invoke-RestMethod "$base/discovery/services/login" -TimeoutSec 2 | Out-Null; $true } catch { $false } }

if (-not (Test-Backend)) {
    Write-Host "Starting back-end on $base ..."
    Start-Process -FilePath $py -ArgumentList '-u', "`"$root\tools\mock-backend\backend.py`"", '--port', $port, '--public-host', $public `
        -WorkingDirectory $root -WindowStyle Minimized -RedirectStandardOutput "$root\build\backend-out.log" -RedirectStandardError "$root\build\backend-err.log"
    for ($i = 0; $i -lt 20 -and -not (Test-Backend); $i++) { Start-Sleep 1 }
    if (-not (Test-Backend)) { Write-Host 'Back-end did not start, see build\backend-err.log'; Read-Host 'Press Enter'; exit 1 }
}

Start-Process -FilePath $java -WorkingDirectory "$root\bin\client" `
    -ArgumentList '-jar', 'brainout-desktop.jar', '--unsafe', '--env', "$base/environment" `
    -RedirectStandardOutput "$root\build\client-last.log" -RedirectStandardError "$root\build\client-last.err"
