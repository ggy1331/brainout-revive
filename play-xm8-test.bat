@echo off
rem Combined test build: XM8 and Gepard, deathmatch, default 4 bots.
rem Usage: play-xm8-test.bat [bots]
set "B=%~1"
if "%B%"=="" set B=4
call "%~dp0play-match.bat" deathmatch - xm8-gepard %B%
