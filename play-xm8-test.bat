@echo off
rem TEST build with the new XM8 rifle (branch xm8, separate folder brainout-xm8).
rem Deathmatch, everyone (you and bots) gets only the XM8.
rem Usage: play-xm8-test.bat [bots]   (default 4)
set "B=%~1"
if "%B%"=="" set B=4
call "%~dp0play-match.bat" deathmatch - xm8-only %B%
