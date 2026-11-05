@echo off
rem Capture the flag on bunker_ctf. Usage: play-ctf.bat [bots] [preset]   (default 8 bots)
rem Note: bots fight but do not carry flags (the original game has no CTF logic for bots).
set "B=%~1"
if "%B%"=="" set "B=8"
set "P=%~2"
if "%P%"=="" set "P=-"
call "%~dp0play-match.bat" ctf bunker_ctf %P% %B%
