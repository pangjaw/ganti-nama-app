@echo off
echo Memantau log build... (Ctrl+C untuk berhenti)
echo Log: %~dp0build.log
echo.
powershell -Command "Get-Content '%~dp0build.log' -Wait -Tail 30"
