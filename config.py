# config.py

# Discord Bot Settings
# Get your token from https://discord.com/developers/applications
# Make sure to enable the 'Message Content Intent'!
BOT_TOKEN = "MTQ4MDI3NDU1OTUwNzc2MzQ0NA.Gl-5Vq.a5POwS2O19zTCyDtl84DQyoxOfh0GtCRqDMGzM"
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