@echo off
chcp 65001 >nul
rem Connect to a BRAIN / OUT server by IP (LAN / Radmin VPN).
rem Usage: connect.bat [IP] [NAME]   - without arguments it asks.
rem The last IP and name are remembered in connect-last.txt.
setlocal
cd /d "%~dp0"

set "IP=%~1"
set "NAME=%~2"
set "LAST_IP="
set "LAST_NAME="
if exist connect-last.txt (
    for /f "usebackq tokens=1,2" %%a in ("connect-last.txt") do (
        set "LAST_IP=%%a"
        set "LAST_NAME=%%b"
    )
)

if "%IP%"=="" (
    if defined LAST_IP (
        set /p "IP=IP хоста [Enter = %LAST_IP%]: "
    ) else (
        set /p "IP=IP хоста (Radmin VPN, например 26.x.x.x): "
    )
)
if "%IP%"=="" set "IP=%LAST_IP%"
if "%IP%"=="" (
    echo Не указан IP.
    pause
    exit /b 1
)

if "%NAME%"=="" (
    if defined LAST_NAME (
        set /p "NAME=Ваше имя [Enter = %LAST_NAME%]: "
    ) else (
        set /p "NAME=Ваше имя (латиница/цифры, без пробелов): "
    )
)
if "%NAME%"=="" set "NAME=%LAST_NAME%"
if "%NAME%"=="" set "NAME=%USERNAME%"

> connect-last.txt echo %IP% %NAME%

for /f %%i in ('powershell -NoProfile -Command "[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('%IP%;36555;36556;36557'))"') do set "LOC=%%i"

rem Java: bundled jre -> JDK 17 -> java from PATH
set "JAVA=java"
if exist "C:\Program Files\Java\jdk-17\bin\java.exe" set "JAVA=C:\Program Files\Java\jdk-17\bin\java.exe"
if exist "%~dp0jre\bin\java.exe" set "JAVA=%~dp0jre\bin\java.exe"

rem Client folder: friend package layout or the dev repo layout
set "CLIENT=%~dp0client"
if not exist "%CLIENT%\brainout-desktop.jar" set "CLIENT=%~dp0bin\client"

echo Подключаемся к %IP% как %NAME% ...
echo Лог: %~dp0client-last.log
cd /d "%CLIENT%"
start "BrainOut client" cmd /c ""%JAVA%" -jar brainout-desktop.jar --offline --unsafe --name %NAME% --connect brainout://%LOC% > "%~dp0client-last.log" 2>&1"
endlocal
