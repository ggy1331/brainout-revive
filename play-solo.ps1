# Single player PvE in the Conflict Zone on this PC: a local back-end (tools/mock-backend in --solo mode)
# + a local Free Play server for one player + the client. No connection to the host is needed.
# The progress (profile, stash, rubles) is synced with the host's online back-end when it is reachable:
# before the game and after it. Usage: play-solo.bat [NICK] [HOST_IP]
param([string]$Name = "", [string]$HostIp = "", [switch]$SyncOnly)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# last host IP / nick: shared with connect-online.bat
$last = Join-Path $root "connect-online-last.txt"
$lastIp = ""; $lastName = ""
if (Test-Path $last) {
    $parts = ((Get-Content $last -TotalCount 1) -split "\s+") | Where-Object { $_ }
    if ($parts.Count -ge 1) { $lastIp = $parts[0] }
    if ($parts.Count -ge 2) { $lastName = $parts[1] }
}
if (-not $Name) { $Name = $lastName }
if (-not $Name) { $Name = Read-Host "Ваш ник (латиница/цифры, без пробелов)" }
if (-not $Name) { $Name = $env:USERNAME }
if (-not $HostIp) { $HostIp = $lastIp }

# layouts: friend package (python\, backend\, server\, client\, jre\) or the dev repo
$python = Join-Path $root "python\python.exe"
if (-not (Test-Path $python)) { $python = Join-Path $root "build\pyenv\Scripts\python.exe" }
$backend = Join-Path $root "backend\backend.py"
if (-not (Test-Path $backend)) { $backend = Join-Path $root "tools\mock-backend\backend.py" }
$server = Join-Path $root "server"
if (-not (Test-Path "$server\brainout-server.jar")) { $server = Join-Path $root "bin\server" }
$client = Join-Path $root "client"
if (-not (Test-Path "$client\brainout-desktop.jar")) { $client = Join-Path $root "bin\client" }
$java = "java"
if (Test-Path "C:\Program Files\Java\jdk-17\bin\java.exe") { $java = "C:\Program Files\Java\jdk-17\bin\java.exe" }
if (Test-Path (Join-Path $root "jre\bin\java.exe")) { $java = Join-Path $root "jre\bin\java.exe" }
foreach ($p in @($python, $backend, "$server\brainout-server.jar", "$client\brainout-desktop.jar")) {
    if (-not (Test-Path $p)) { throw "Не найдено: $p" }
}

$data = Join-Path $root ("solo-data\" + $Name)
$logs = Join-Path $root "solo-data\logs"
New-Item -ItemType Directory -Force $logs | Out-Null
$port = 9521
$common = @($backend, "--port", "$port", "--solo", $Name, "--data", $data, "--server-dir", $server,
            "--logs-dir", $logs, "--java", $java)
if ($HostIp) { $common += @("--sync-host", "http://${HostIp}:9511") }

$env:PYTHONIOENCODING = "utf-8"
if ($SyncOnly) {
    # connect-online.bat: send the solo progress to the host before playing online
    if ($HostIp -and (Test-Path $data)) {
        & $python @common "--sync-only" 2>&1 | Where-Object { "$_" -match "Sync with" } | ForEach-Object { Write-Host "$_" }
    }
    exit 0
}

Write-Host "Одиночная Зона конфликта: $Name" -ForegroundColor Green
if ($HostIp) { Write-Host "Синхронизация прогресса с хостом $HostIp" } else { Write-Host "Хост не указан: прогресс только на этом ПК" }

$backendLog = Join-Path $logs "backend.log"
$proc = Start-Process -FilePath $python -ArgumentList ($common | ForEach-Object { '"' + $_ + '"' }) `
    -RedirectStandardOutput $backendLog -RedirectStandardError (Join-Path $logs "backend.err") -PassThru -WindowStyle Hidden
try {
    $ok = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        if ($proc.HasExited) { break }
        try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$port/game/status" | Out-Null; $ok = $true; break } catch {}
    }
    if (-not $ok) { Get-Content $backendLog, (Join-Path $logs "backend.err") -ErrorAction SilentlyContinue | Select-Object -Last 20; throw "Локальный бэкенд не запустился" }
    Select-String -Path $backendLog -Pattern "Sync with" -Encoding UTF8 | ForEach-Object { Write-Host $_.Line }

    Write-Host "Запуск игры... (сервер Зоны поднимается ~30 с после входа)"
    $env:DESKTOP_PROFILE_NAME = $Name
    $clientLog = Join-Path $root "client-solo.log"
    $c = Start-Process -FilePath $java -WorkingDirectory $client -PassThru -RedirectStandardOutput $clientLog `
        -RedirectStandardError (Join-Path $root "client-solo.err") `
        -ArgumentList @("-jar", "brainout-desktop.jar", "--unsafe", "--name", $Name, "--env", "http://127.0.0.1:$port/environment")
    $c.WaitForExit()
    Write-Host "Игра закрыта, сохраняю прогресс..."
    Start-Sleep -Seconds 6  # the game server saves the profile when the player leaves
}
finally {
    # stop the local back-end and the game servers it started
    # (the whole tree: the venv python.exe is a launcher, game servers are its grandchildren)
    $all = Get-CimInstance Win32_Process
    $tree = @($proc.Id); $i = 0
    while ($i -lt $tree.Count) {
        $tree += @($all | Where-Object { $_.ParentProcessId -eq $tree[$i] } | ForEach-Object { $_.ProcessId })
        $i++
    }
    [array]::Reverse($tree)
    foreach ($id in $tree) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
}

if ($HostIp) {
    & $python @common "--sync-only" 2>&1 | Where-Object { "$_" -match "Sync with" } | ForEach-Object { Write-Host "$_" }
}
Write-Host "Готово."
