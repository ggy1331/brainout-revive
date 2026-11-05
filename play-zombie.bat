@echo off
rem Zombie co-op: players vs waves of armed zombies (halloween map, bin\server\zombie-set.json).
rem Usage: play-zombie.bat [number_of_allied_bots]   (default 0)
rem Logs: build\server-last.log, build\client-last.log
setlocal
set "JAVA=java"
if exist "C:\Program Files\Java\jdk-17\bin\java.exe" set "JAVA=C:\Program Files\Java\jdk-17\bin\java.exe"
set BOTS=%1
if "%BOTS%"=="" set BOTS=0
set server_settings={"bots":%BOTS%}
set "SLOG=%~dp0build\server-last.log"
if not exist "%~dp0build" mkdir "%~dp0build"
if exist "%SLOG%" del "%SLOG%"
start "BrainOut server (zombies, allied bots: %BOTS%)" /D "%~dp0bin\server" powershell -NoProfile -ExecutionPolicy Bypass -Command "& $env:JAVA -jar brainout-server.jar no 36555,36556,36557 --offline --settings server-settings.json --maps zombie-set.json 2>&1 | ForEach-Object { \"$_\" } | Tee-Object -FilePath $env:SLOG"
call :wait_server
start "BrainOut client" /D "%~dp0bin\client" cmd /c ""%JAVA%" -jar brainout-desktop.jar --offline --unsafe --connect brainout://bG9jYWxob3N0OzM2NTU1OzM2NTU2OzM2NTU3 > ..\..\build\client-last.log 2>&1"
endlocal
exit /b 0

:wait_server
rem wait until the server finished loading (max ~90 s)
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
