@echo off
chcp 65001 >nul
rem ONLINE mode: connect to the host's back-end (Radmin VPN / LAN): hub, rubles, market, clans, friends.
rem Usage: connect-online.bat [IP] [NICKNAME]   - without arguments it asks.
rem The last IP and nickname are remembered in connect-online-last.txt.
setlocal
cd /d "%~dp0"

set "IP=%~1"
set "NAME=%~2"
set "LAST_IP="
set "LAST_NAME="
if exist connect-online-last.txt (
    for /f "usebackq tokens=1,2" %%a in ("connect-online-last.txt") do (
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
        set /p "NAME=Ваш ник [Enter = %LAST_NAME%]: "
    ) else (
        set /p "NAME=Ваш ник (латиница/цифры, без пробелов): "
    )
)
if "%NAME%"=="" set "NAME=%LAST_NAME%"
if "%NAME%"=="" set "NAME=%USERNAME%"

> connect-online-last.txt echo %IP% %NAME%
rem own online account per nickname (also on one PC)
set "DESKTOP_PROFILE_NAME=%NAME%"

rem Java: bundled jre -> JDK 17 -> java from PATH
set "JAVA=java"
if exist "C:\Program Files\Java\jdk-17\bin\java.exe" set "JAVA=C:\Program Files\Java\jdk-17\bin\java.exe"
if exist "%~dp0jre\bin\java.exe" set "JAVA=%~dp0jre\bin\java.exe"

rem Client folder: friend package layout or the dev repo layout
set "CLIENT=%~dp0client"
if not exist "%CLIENT%\brainout-desktop.jar" set "CLIENT=%~dp0bin\client"

echo Онлайн у %IP% как %NAME% ...
echo Лог: %~dp0client-last.log
cd /d "%CLIENT%"
start "BrainOut client" cmd /c ""%JAVA%" -jar brainout-desktop.jar --unsafe --name %NAME% --env http://%IP%:9511/environment > "%~dp0client-last.log" 2>&1"
endlocal
