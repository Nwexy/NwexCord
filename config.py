# config.py

# Discord Bot ayarları
# Token'ı https://discord.com/developers/applications adresinden almalısınız.
# 'Message Content Intent' ayarının açık olduğundan emin olun!
BOT_TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
PREFIX = "."

# Eski Webhook ayarı (Yedek olarak durabilir)
WEBHOOK_URL = "PUT_YOUR_WEBHOOK_URL_HERE"

# Hazır komutlar
COMMANDS = {
    "status": "systeminfo",
    "disk": "wmic logicaldisk get caption,freeheight,size",
    "memory": "systeminfo | findstr /C:\"Total Physical Memory\"",
    "uptime": "net statistics server",
    "users": "query user",
    "processes": "tasklist | more"
}