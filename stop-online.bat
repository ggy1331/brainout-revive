@echo off
rem Stops the local back-end and every game server it started.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'mock-backend[\\/]backend\.py|brainout-server\.jar' -and $_.Name -match 'python|java' } | ForEach-Object { Write-Host ('stop ' + $_.ProcessId + ' ' + $_.Name); Stop-Process -Id $_.ProcessId -Force }"
