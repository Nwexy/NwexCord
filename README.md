# NwexCord
A powerful, interactive Discord bot for remote system management and fun interactions, entirely controllable through Discord.

## Features

- **Automated setup**: `start.bat` installs dependencies, checks for Python, securely injects your bot token, and handles execution with a sleek colorful launcher.
- **Detailed System Information**: When the bot connects, it provides detailed client specs (IP, Location, OS, Resources, Antivirus hook, Firewall active state).
- **Remote `cmd` / `powershell` Shell Execution**: Use the `.shell <command>` command to execute remote code.
- **Interactive 🧰 Tools Panel**: Use Discord Select UI & Buttons to manage the client system:
  - **Process & Service Manager**: List, monitor, or kill processes and services.
  - **Active Windows Manager**: Enumerate and focus specific application windows.
  - **TCP Connections Manager**: Monitor active network connections.
  - **Windows Registry Editor**: View, modify, or add registry keys remotely.
  - **Startup App Manager**: Examine and configure run-at-startup programs.
  - **Installed Programs**: List all software packages.
  - **Clipboard Monitor**: View the remote client's clipboard contents.
- **Interactive 🎉 Fun Panel**: Have some fun with the client system directly from Discord:
  - **Client Chat**: A real-time 2-way chat between the Discord channel and a prompt running on the client PC.
  - **Text-to-Speech (TTS)**: Speak text aloud on the client PC using SAPI.SpVoice.
  - **System Trolls**: Manipulate the Clock, Screen, Desktop, Mouse, or Volume.
  - **Message Generator**: Trigger customizable native MessageBoxes and Balloon Tooltips with custom icons and buttons.
  - **Open URLs**: Launch websites directly onto the default browser.

## Getting Started
1. Run `start.bat` in the root folder.
2. If this is your first time, the launcher will prompt you for your Discord Bot Token (which will be securely injected into `config.py`).
3. Enjoy! The bot will notify you in Discord as soon as it boots up.
