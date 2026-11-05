@echo off
rem Custom match: pick mode, map, rules preset and number of bots.
rem Usage: play-match.bat [mode] [map] [preset] [bots]      use - to skip a value
rem   mode:   normal deathmatch domination assault ctf foxhunt gungame
rem   map:    see bin\server\maps-set.json ("maps"), e.g. hospital, bunker_ctf, mall
rem   preset: knife-only toz34-only classic-only no-primary hard super-hard
rem           (defined in bin\server\server-settings.json, "presets")
rem   bots:   number (default 8)
rem Examples:
rem   play-match.bat gungame mall - 6
rem   play-match.bat deathmatch - knife-only 4
rem   play-match.bat normal hospital super-hard
rem The chosen mode stays for the following matches (keep-mode); maps rotate among
rem the maps that support it. Details: docs\match-rules.md
rem Logs: build\server-last.log, build\client-last.log
setlocal
set "JAVA=java"
if exist "C:\Program Files\Java\jdk-17\bin\java.exe" set "JAVA=C:\Program Files\Java\jdk-17\bin\java.exe"

set "MODE=%~1"
set "MAP=%~2"
set "PRESET=%~3"
set "BOTS=%~4"
if "%MODE%"=="-" set "MODE="
if "%MAP%"=="-" set "MAP="
if "%PRESET%"=="-" set "PRESET="
if "%BOTS%"=="-" set "BOTS="
if "%BOTS%"=="" set "BOTS=8"

set "RS={"keep-mode":true"
if not "%MODE%"=="" set "RS=%RS%,"mode":"%MODE%""
if not "%MAP%"=="" set "RS=%RS%,"map":"%MAP%""
if not "%PRESET%"=="" set "RS=%RS%,"preset":"%PRESET%""
set "RS=%RS%}"
set "room_settings=%RS%"
set server_settings={"bots":%BOTS%}
echo Match: mode=%MODE% map=%MAP% preset=%PRESET% bots=%BOTS%
echo room_settings=%room_settings%

set "SLOG=%~dp0build\server-last.log"
if not exist "%~dp0build" mkdir "%~dp0build"
if exist "%SLOG%" del "%SLOG%"
start "BrainOut server (match: %MODE% %MAP% %PRESET%)" /D "%~dp0bin\server" powershell -NoProfile -ExecutionPolicy Bypass -Command "& $env:JAVA -jar brainout-server.jar no 36555,36556,36557 --offline --settings server-settings.json --maps maps-set.json 2>&1 | ForEach-Object { \"$_\" } | Tee-Object -FilePath $env:SLOG"
call :wait_server
start "BrainOut client" /D "%~dp0bin\client" cmd /c ""%JAVA%" -jar brainout-desktop.jar --offline --unsafe --connect brainout://bG9jYWxob3N0OzM2NTU1OzM2NTU2OzM2NTU3 > ..\..\build\client-last.log 2>&1"
endlocal
exit /b 0

:wait_server
echo Waiting for the server to start...
for /l %%i in (1,1,90) do (
    timeout /t 1 /nobreak >nul
    if exist "%SLOG%" (
        type "%SLOG%" 2>nul | find "Initialized!" >nul && exit /b 0
        type "%SLOG%" 2>nul | find "ERROR: Failed to load." >nul && (echo Server failed to start, see build\server-last.log & pause & exit /b 1)
    )
)
echo Server did not report ready in 90 s, starting the client anyway.
exit /b 0
