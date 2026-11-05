@echo off
rem Regular modes (random map/mode rotation from bin\server\maps-set.json) offline with bots.
rem Usage: play-bots.bat [number_of_bots]   (default 8)
rem Client log -> build\client-last.log
set "JAVA=java"
if exist "C:\Program Files\Java\jdk-17\bin\java.exe" set "JAVA=C:\Program Files\Java\jdk-17\bin\java.exe"
set BOTS=%1
if "%BOTS%"=="" set BOTS=8
set server_settings={"bots":%BOTS%}
start "BrainOut server (bots: %BOTS%)" /D "%~dp0bin\server" "%JAVA%" -jar brainout-server.jar no 36555,36556,36557 --offline --settings server-settings.json --maps maps-set.json
timeout /t 8 /nobreak >nul
start "BrainOut client" /D "%~dp0bin\client" cmd /c ""%JAVA%" -jar brainout-desktop.jar --offline --unsafe --connect brainout://bG9jYWxob3N0OzM2NTU1OzM2NTU2OzM2NTU3 > ..\..\build\client-last.log 2>&1"
