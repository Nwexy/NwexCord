@echo off
set WEBHOOK_URL="https://discord.com/api/webhooks/1480284001951289415/CMenimQeN3yvdcv3xEqM-mXW4V4tBy-bKs2TI7UqbbSVvFG0m5aJJGYv_UozCJ0QrSZ7"

if "%~1"=="" (
    echo Usage: %0 "command"
    echo Example: %0 "dir"
    pause
    exit /b 1
)

py NwexCord.py --webhook %WEBHOOK_URL% --command "%~1"
