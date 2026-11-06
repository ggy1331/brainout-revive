@echo off
rem ONLINE mode with the local back-end imitation (tools\mock-backend): main menu -> hub -> matches,
rem profiles, rubles, market, clans, friends are kept by the back-end in backend-data\.
rem Game servers are started by the back-end on demand (logs: build\rooms\).
rem Usage: play-online.bat [nickname]      (default: Windows user name)
rem Friends: connect-online.bat with your Radmin IP. Stop everything: stop-online.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\mock-backend\play-online.ps1" %*
