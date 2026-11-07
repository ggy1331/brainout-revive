@echo off
rem Deathmatch with the FULL arsenal (all weapons incl. XM8 and Gepard), default 4 bots.
rem Usage: play-xm8-test.bat [bots]
rem Restricted tests: play-match.bat deathmatch - xm8-gepard or xm8-only or gepard-only [bots]
set "B=%~1"
if "%B%"=="" set B=4
call "%~dp0play-match.bat" deathmatch - - %B%
