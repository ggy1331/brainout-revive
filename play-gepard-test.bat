@echo off
rem Gepard concept test: deathmatch, Gepard-only primary weapons, default 4 bots.
set "B=%~1"
if "%B%"=="" set B=4
call "%~dp0play-match.bat" deathmatch - gepard-only %B%
