@echo off
set LOG="C:\Users\dikarm\.gemini\antigravity\brain\21c14e94-9b99-41bd-a2ce-33bedf0360a8\.system_generated\tasks\task-759.log"
echo Memantau: %LOG%
echo Ctrl+C untuk berhenti
echo.
powershell -Command "Get-Content %LOG% -Wait -Tail 30"
