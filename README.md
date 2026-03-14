# NwexCord
A powerful, interactive Discord bot for remote system management and fun interactions, entirely controllable through Discord.

## Key Features

- **Automated Setup**: `start.bat` installs dependencies, checks for Python, securely injects your bot token, and handles execution with a sleek colorful launcher.
- **Detailed System Information**: Upon connection, the bot provides comprehensive system specs including IP, Geo-Location, OS details, Hardware (CPU/GPU/RAM), Antivirus status, and Firewall state.
- **Remote Shell Execution**: Execute any CMD or PowerShell command directly using `.shell <command>`.
- **4 Custom Interactive Panels**: Large, well-organized dashboard with buttons and dropdowns for everything.

---

## 🧰 Tools Panel
Manage the client system with professional-grade utilities:
- **Registry Editor**: Full interactive tree navigation, view/edit/add/delete registry values.
- **Active Windows Manager**: List all visible windows and close them remotely.
- **TCP Connections Manager**: Monitor active network ports and kill associated PIDs.
- **Process & Service Manager**: Real-time listing with restart, suspend, and terminate controls.
- **Startup Manager**: Manage items in Startup folders, Registry Run keys, and Scheduled Tasks (fully paginated).
- **Installed Programs**: Browse and uninstall software packages.
- **Clipboard & Services**: View clipboard history and manage system services.

## ⚙️ System Panel
Surveillance and system-level configuration:
- **Screenshot & Webcam**: Capture screenshots (multi-monitor support) or webcam photos instantly.
- **Live Screen**: Real-time screen streaming via a secure `cloudflared` tunnel (watch in browser).
- **Microphone Listener**: Record and listen to the remote microphone for custom durations.
- **KeyLogger**: Stealthily log keystrokes and retrieve them via Discord.
- **Performance Monitor**: Real-time CPU, RAM, and Disk usage statistics.
- **UAC Bypass**: Quickly toggle User Account Control states.

## 🪟 Windows Panel
Direct control over Windows features and defenses:
- **Interactive File Manager**: 
  - Hierarchical browsing with context-menu actions.
  - File operations: Download, Upload, Delete, Rename, Execute (Hidden/RunAs).
  - Advanced: **Lock/Unlock folders** (icacls), **Show/Hide files** (attrib), **Edit text files**, **Set Wallpaper**, and **Download Folder as ZIP**.
- **Security Toggles**: 
  - **WDDisable**: Interactive **Enable/Disable toggle** for Windows Defender Real-Time Protection.
  - **WDExclusion**: Add specific paths to Defender's exclusion list.
  - **Firewall & Task Manager**: Toggle system-wide Firewall or Task Manager access (auto-fixes registry locks).
- **System Services**: Toggle Windows Update or Registry Editor (Regedit) access.
- **Elevated Execution**: Run any file with administrative privileges.

## 🎉 Fun Panel
Interactive "troll" features and communication tools:
- **Client Chat**: 2-way real-time chat between Discord and a popup on the target PC.
- **Text-to-Speech (TTS)**: Speak any text aloud using the system's voice.
- **Message Generator**: Trigger custom native MessageBoxes or Balloon Tooltips with custom icons/buttons.
- **Remote Trolls**: Toggle the Clock visibility, rotate the Screen, hide Desktop icons, or swap Mouse buttons.
- **Open URLs**: Launch any website directly in the target's default browser.

## 🔓 Recovery Panel
High-speed extraction and organization of sensitive data into structured ZIP archives:
- **Browser Recovery**: Extracts **Passwords**, **Netscape Cookies**, **Autofill Data**, and **Credit Cards** from all Chromium-based browsers (Chrome, Edge, Brave, Opera, Vivaldi, etc.).
- **Smart Organization**: Automatically organizes data into `Passwords_Date/Browser/Profile/` subfolders within the ZIP.
- **Steam Token**: Extracts only the essential **SSFN Auth-Tokens** (machine-auth) needed for session takeover.
- **Discord Token**: Scans all Discord clients (Stable, Canary, PTB) and browser local storage for active session tokens.
- **WiFi Keys**: Retrieves all saved Wi-Fi network names and clear-text passwords.
- **RAR/ZIP Export**: All recovered data is neatly packaged into text files and sent as a single compressed archive.

---

## 🛠️ Exe Builder (`builder.py`)
Compile NwexCord into a standalone, hidden `.exe` payload with a custom, modern UI:
- **Activity-Based UI**: Sleek dual-screen interface (Main & Settings) with custom Nwexy icon.
- **Persistence Options**: Inject Startup folder links, Registry Run keys, and Schtasks.
- **Dynamic Install Paths**: Choose from `%AppData%`, `%ProgramData%`, etc., and optionally nest inside a custom **Subdirectory**.
- **Security Evasion**: Automatically appends the drop location to Windows Defender Exclusions (WDEX).

---

## 🚀 Getting Started
1. Run `start.bat` in the root folder.
2. Choose your run mode via the interactive menu: **Run Locally** or **Build EXE**.
3. If building, the modern GUI allows you to securely inject your Discord Bot Token, set the icon, and configure persistence.
4. Once deployed on the target system, the bot will automatically notify your Discord server with a full system report.
5. **Self-Destruct Mechanisms**: Click the red `Uninstall` button on the bot's main startup view to wipe all registry keys, scheduled tasks, startup folder links, WD exclusions, and fully delete the core executable from the disk, leaving no traces behind.

## Requirements
- Windows OS (Target)
- Python 3.x
- Discord Bot Token

---
*Disclaimer: This tool is for educational and authorized testing purposes only. Use it responsibly.*
