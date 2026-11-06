@echo off
rem ONLINE mode with the local back-end imitation (tools\mock-backend): main menu -> hub -> matches,
rem profiles, rubles and market are kept by the back-end in backend-data\.
rem Game servers are started by the back-end on demand (logs: build\rooms\).
rem To stop everything: close the game, then stop-online.bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\mock-backend\play-online.ps1" %*
