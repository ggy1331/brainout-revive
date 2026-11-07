@echo off
chcp 65001 >nul
rem Single player PvE Conflict Zone on this PC (no host needed). Progress syncs with the host when reachable.
rem Usage: play-solo.bat [NICK] [HOST_IP]   (defaults: from connect-online-last.txt)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0play-solo.ps1" %*
pause
