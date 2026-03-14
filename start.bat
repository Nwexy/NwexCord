@echo off
chcp 65001 >nul
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

:MENU
echo ========================================
echo Please select an action:
echo [1] Start NwexCord Locally
echo [2] Build NwexCord Executable (GUI)
echo ========================================
set /p "USER_CHOICE=Choice (1-2): "

if "!USER_CHOICE!"=="1" goto :LOCAL_START
if "!USER_CHOICE!"=="2" goto :BUILD_START
echo [X] Invalid choice. Please press 1 or 2.
echo.
goto :MENU

:BUILD_START
if not exist builder.py (
    echo [X] builder.py not found!
    pause
    exit /b 1
)
echo [*] Starting NwexCord Builder...
!PY_CMD! builder.py
exit /b 0

:LOCAL_START

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

!PY_CMD! -m pip install -r requirements.txt --user
if !errorlevel! neq 0 (
    echo.
    echo [X] Failed to install dependencies. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo [+] Dependencies are verified.
echo.

:: 4. Install Cloudflare Tunnel
echo [*] Checking Cloudflared Tunnel...
if not exist cloudflared.exe (
    echo [*] Downloading cloudflared.exe...
    curl -L -o cloudflared.exe "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [X] Failed to download cloudflared.exe. Live Screen may not work.
    ) else (
        echo [+] Cloudflared installed successfully.
    )
) else (
    echo [+] Cloudflared is already installed.
)
echo.

:: 5. Run the bot
echo ========================================
echo [^>] Starting NwexCord...
echo ========================================
echo.
ping -n 5 127.0.0.1 >nul
cls
setlocal disabledelayedexpansion
echo.
for /f "delims=: tokens=1*" %%a in ('findstr /b "::LOGO:" "%~f0"') do @(
    if "%%b"=="" (
        echo/
    ) else (
        echo/%%b
    )
)
endlocal
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

::LOGO:
::LOGO:
::LOGO:[34m                        ███╗   ██╗██╗    ██╗███████╗██╗  ██╗ ██████╗ ██████╗ ██████╗ ██████╗ [0m
::LOGO:[94m                        ████╗  ██║██║    ██║██╔════╝╚██╗██╔╝██╔════╝██╔═══██╗██╔══██╗██╔══██╗[0m
::LOGO:[36m                        ██╔██╗ ██║██║ █╗ ██║█████╗   ╚███╔╝ ██║     ██║   ██║██████╔╝██║  ██║[0m
::LOGO:[36m                        ██║╚██╗██║██║███╗██║██╔══╝   ██╔██╗ ██║     ██║   ██║██╔══██╗██║  ██║[0m
::LOGO:[94m                        ██║ ╚████║╚███╔███╔╝███████╗██╔╝ ██╗╚██████╗╚██████╔╝██║  ██║██████╔╝[0m
::LOGO:[34m                        ╚═╝  ╚═══╝ ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ [0m
::LOGO:
::LOGO:                                       [36mWebsite   : https://nwexy.com[0m 
::LOGO:                                       [36mGitHub    : https://github.com/nwexy[0m 
::LOGO:
::LOGO:[90;1m========================================================================================================================[0m
