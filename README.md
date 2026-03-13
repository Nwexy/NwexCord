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
- **Startup Manager**: Manage items in Startup folders, Registry Run keys, and Scheduled Tasks.
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

---

## Getting Started
1. Run `start.bat` in the root folder.
2. If this is your first time, the launcher will prompt you for your **Discord Bot Token** (securely saved in `config.py`).
3. The bot will automatically notify you in Discord with a full system report once it's active.

## Requirements
- Windows OS (Target)
- Python 3.x
- Discord Bot Token

---
*Disclaimer: This tool is for educational and authorized testing purposes only. Use it responsibly.*
