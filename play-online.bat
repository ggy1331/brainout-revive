@echo off
rem ONLINE mode with the local back-end imitation (tools\mock-backend): profiles are kept by the
rem back-end in backend-data\, like on the official servers.
rem Usage: play-online.bat [bots] [mode]     mode: bots (default) or free
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\mock-backend\play-online.ps1" %*
