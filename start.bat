@echo off
setlocal enabledelayedexpansion
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
) else (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py"
    ) else (
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
        ) else (
            echo.
            echo [X] Winget installation failed. 
            echo [!] Please install Python manually from https://www.python.org/downloads/
            pause
            exit /b 1
        )
    )
)

echo [+] Python found: !PY_CMD!
echo.

:: 2. Check and ask for Token
echo [*] Checking Bot Token configuration...

:: Inline python to check if token is "YOUR_BOT_TOKEN_HERE" or empty
!PY_CMD! -c "import config; exit(1) if config.BOT_TOKEN in ['YOUR_BOT_TOKEN_HERE', ''] else exit(0)" >nul 2>&1

if !errorlevel! neq 0 (
    echo [!] Bot Token is not configured!
    echo.
    set /p "USER_TOKEN=Please paste your Discord Bot Token: "
    
    if "!USER_TOKEN!"=="" (
        echo [X] You must provide a token to start the bot.
        pause
        exit /b 1
    )
    
    :: Write a temp script to update config.py securely
    echo import re ^> _update_token.py
    echo content=open('config.py','r',encoding='utf-8').read() ^>^> _update_token.py
    echo content=re.sub(r'BOT_TOKEN\s*=\s*\".*?\"', 'BOT_TOKEN = \"'!USER_TOKEN!'\"', content) ^>^> _update_token.py
    echo open('config.py','w',encoding='utf-8').write(content) ^>^> _update_token.py
    
    !PY_CMD! _update_token.py
    del _update_token.py >nul 2>&1
    
    echo [+] Token saved to config.py!
    echo.
) else (
    echo [+] Token is already configured in config.py.
    echo.
)

:: 3. Install requirements
echo [*] Checking dependencies...
!PY_CMD! -m pip install -r requirements.txt >nul
if !errorlevel! equ 0 (
    echo [+] Dependencies are installed.
) else (
    echo [X] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)
echo.

:: 4. Run the bot
echo ========================================
echo [>] Starting NwexCord...
echo ========================================
echo.

!PY_CMD! NwexCord.py

echo.
echo [!] Bot crashed or stopped.
pause
