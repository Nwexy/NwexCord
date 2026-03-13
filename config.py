# config.py

# Discord Bot Settings
# Get your token from https://discord.com/developers/applications
# Make sure to enable the 'Message Content Intent'!
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
PREFIX = "."

# Pre-defined commands  
COMMANDS = {
    "status": "systeminfo",
    "disk": "wmic logicaldisk get caption,freeheight,size",
    "memory": "systeminfo | findstr /C:\"Total Physical Memory\"",
    "uptime": "net statistics server",
    "users": "query user",
    "processes": "tasklist | more"
}
