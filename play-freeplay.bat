@echo off
rem Free Play offline: server + client. Close the server window to stop it.
rem Client log -> build\client-last.log
set "JAVA=java"
if exist "C:\Program Files\Java\jdk-17\bin\java.exe" set "JAVA=C:\Program Files\Java\jdk-17\bin\java.exe"
set game_max_players=4
start "BrainOut server (Free Play)" /D "%~dp0bin\server" "%JAVA%" -jar brainout-server.jar --offline --mode free --settings server-free.json --map freeplay-maps.shuffle
timeout /t 8 /nobreak >nul
start "BrainOut client" /D "%~dp0bin\client" cmd /c ""%JAVA%" -jar brainout-desktop.jar --offline --unsafe --connect brainout://bG9jYWxob3N0OzM2NTU1OzM2NTU2OzM2NTU3 > ..\..\build\client-last.log 2>&1"
