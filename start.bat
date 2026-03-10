@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title NwexCord - All-In-One Launcher

echo ========================================
echo NwexCord Bot Setup ^& Launcher
echo ========================================
echo.

:: 1. Detect Python
echo [*] Checking Python installation...
set "PY_CMD="

python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
    goto :PYTHON_FOUND
)

py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=py"
    goto :PYTHON_FOUND
)

echo [!] Python is not installed or not in PATH.
echo [?] Attempting to install Python 3.11 via winget...
echo.
winget install -e --id Python.Python.3.11 --source winget --silent --accept-package-agreements --accept-source-agreements

if !errorlevel! equ 0 (
    echo.
    echo [+] Python installation successful!
    echo [!] IMPORTANT: The terminal must be restarted for Windows to see Python.
    echo [!] Please close this window, and then DOUBLE-CLICK start.bat again.
    pause
    exit /b 0
)

echo.
echo [X] Winget installation failed or is not available. 
echo [!] Please install Python manually from https://www.python.org/downloads/
echo [!] Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:PYTHON_FOUND
echo [+] Python found: !PY_CMD!
echo.

:: 2. Check and ask for Token
echo [*] Checking Bot Token configuration...

if not exist config.py (
    echo [X] config.py not found in current directory!
    pause
    exit /b 1
)

!PY_CMD! -c "import config; exit(1) if not hasattr(config, 'BOT_TOKEN') or config.BOT_TOKEN in ['YOUR_BOT_TOKEN_HERE', ''] else exit(0)" >nul 2>&1

if !errorlevel! equ 0 (
    echo [+] Token is already configured in config.py.
    echo.
    goto :TOKEN_OK
)

echo [!] Bot Token is not configured!
echo.
set /p "USER_TOKEN=Please paste your Discord Bot Token: "

if "!USER_TOKEN!"=="" (
    echo [X] You must provide a token to start the bot.
    pause
    exit /b 1
)

:: Generate update script line by line (no parenthesized blocks!)
echo import re > _update.py
echo try: >> _update.py
echo     content=open('config.py','r',encoding='utf-8').read() >> _update.py
echo     content=re.sub(r'BOT_TOKEN\s*=\s*\".*?\"', 'BOT_TOKEN = \"!USER_TOKEN!\"', content) >> _update.py
echo     open('config.py','w',encoding='utf-8').write(content) >> _update.py
echo     print("[+] Token saved successfully.") >> _update.py
echo except Exception as e: >> _update.py
echo     print(f"[X] Failed to update config.py: {e}") >> _update.py
echo     exit(1) >> _update.py

!PY_CMD! _update.py
set "UPD_ERR=!errorlevel!"
del _update.py >nul 2>&1

if !UPD_ERR! neq 0 (
    pause
    exit /b 1
)
echo.

:TOKEN_OK

:: 3. Install requirements
echo [*] Checking dependencies...
if not exist requirements.txt (
    echo [X] requirements.txt not found!
    pause
    exit /b 1
)

!PY_CMD! -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo.
    echo [X] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo [+] Dependencies are verified.
echo.

:: 4. Run the bot
echo ========================================
echo [^>] Starting NwexCord...
echo ========================================
echo.

if not exist NwexCord.py (
    echo [X] NwexCord.py not found!
    pause
    exit /b 1
)

!PY_CMD! NwexCord.py

echo.
echo [!] Bot has stopped or crashed.
echo [?] Review any error messages above.
pause
