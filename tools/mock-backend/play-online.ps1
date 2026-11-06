# ONLINE mode with the local Anthill imitation (tools/mock-backend):
# starts the backend (if not running), the game server (online, bots) and a client.
# Usage: play-online.bat [bots] [mode]     mode: bots (default) | free
#        $env:BRAINOUT_PUBLIC_HOST = Radmin/LAN IP to let friends use this backend
param([int]$Bots = 8, [string]$Mode = 'bots')
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
    Write-Host "Starting backend on $base ..."
    Start-Process -FilePath $py -ArgumentList '-u', "`"$root\tools\mock-backend\backend.py`"", '--port', $port, '--public-host', $public `
        -WorkingDirectory $root -WindowStyle Minimized -RedirectStandardOutput "$root\build\backend-out.log" -RedirectStandardError "$root\build\backend-err.log"
    for ($i = 0; $i -lt 20 -and -not (Test-Backend); $i++) { Start-Sleep 1 }
    if (-not (Test-Backend)) { Write-Host 'Backend did not start, see build\backend-err.log'; Read-Host 'Press Enter'; exit 1 }
}

$tok = Invoke-RestMethod "$base/login/server-token?name=local-server"
$services = @{}
foreach ($s in 'login','profile','promo','event','game','leaderboard','message','store','social','static','report','blog','market','discovery','environment') { $services[$s] = "$base/$s" }
$env:login_access_token = $tok.token
$env:discovery_services = ($services | ConvertTo-Json -Compress)
$env:server_settings = "{`"bots`":$Bots}"
$env:SLOG = "$root\build\server-last.log"
if (Test-Path $env:SLOG) { Remove-Item $env:SLOG }
$env:JAVA = $java
if ($Mode -eq 'free') { $sargs = '-jar brainout-server.jar --mode free --settings server-free.json --map freeplay-maps.shuffle'; $env:game_max_players = '4' }
else { $sargs = '-jar brainout-server.jar no 36555,36556,36557 --settings server-settings.json --maps maps-set.json' }

Start-Process powershell -WorkingDirectory "$root\bin\server" -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
    "`$host.UI.RawUI.WindowTitle='BrainOut server (online, $Mode)'; & `$env:JAVA $sargs 2>&1 | ForEach-Object { `"`$_`" } | Tee-Object -FilePath `$env:SLOG"

Write-Host 'Waiting for the server to start...'
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep 1
    if ((Test-Path $env:SLOG) -and (Select-String -Path $env:SLOG -Pattern 'Initialized!' -Quiet)) { break }
}

$loc = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("127.0.0.1;36555;36556;36557"))
Start-Process -FilePath $java -WorkingDirectory "$root\bin\client" `
    -ArgumentList '-jar', 'brainout-desktop.jar', '--unsafe', '--env', "$base/environment", '--connect', "brainout://$loc" `
    -RedirectStandardOutput "$root\build\client-last.log" -RedirectStandardError "$root\build\client-last.err"
