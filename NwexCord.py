#!/usr/bin/env python3
"""
NwexCord - Discord Interactive Shell Bot
A tool for executing shell commands via Discord messages
"""

import discord
from discord.ext import commands
import subprocess
import os
import sys
from datetime import datetime
import config

# Bot kurulumu
intents = discord.Intents.default()
intents.message_content = True  # Mesaj içeriğini okuyabilmek için gerekli

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

class ShellExecutor:
    @staticmethod
    def execute(command: str):
        """Sistem komutunu çalıştırır ve çıktıyı döner"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }

@bot.event
async def on_ready():
    client_id = bot.user.id
    invite_link = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot"
    
    print(f'--- NwexCord Aktif ---')
    print(f'Bot Kullanıcı Adı: {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Bulunduğu Sunucu Sayısı: {len(bot.guilds)}')
    print(f'Davet Linki: {invite_link}')
    print(f'----------------------')
    
    if len(bot.guilds) == 0:
        print("UYARI: Bot şu an hiçbir sunucuda ekli değil!")
        print("Lütfen yukarıdaki linki kullanarak botu sunucunuza ekleyin.")
    
    # Botun durumunu (Activity) ayarla
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name=f"{config.PREFIX}shell"
    ))
    
    # Botun ulaştığı ilk kanala "Aktif" mesajı gönder
    sent_message = False
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(f"🚀 **NwexCord Sistemi Başlatıldı!**\nŞu an komutlarınızı bekliyorum. Kullanım: `{config.PREFIX}shell <komut>`")
                    sent_message = True
                    break
                except:
                    continue
        if sent_message: break

@bot.command(name="shell")
async def shell_command(ctx, *, cmd: str):
    """Discord üzerinden komut çalıştırır: .shell dir"""
    
    # Bilgi mesajı gönder
    msg = await ctx.send(f"⚡ Çalıştırılıyor: `{cmd}`...")
    
    # Komutu çalıştır
    result = ShellExecutor.execute(cmd)
    
    # Çıktıyı hazırla
    output = ""
    if result["stdout"]:
        # Discord 2000 karakter sınırı var, son 1500 karakteri alalım
        stdout_text = result["stdout"]
        if len(stdout_text) > 1500:
            stdout_text = "...(kesildi)...\n" + stdout_text[-1500:]
        output += f"**Output:**\n```\n{stdout_text}\n```\n"
        
    if result["stderr"]:
        stderr_text = result["stderr"]
        if len(stderr_text) > 400:
            stderr_text = stderr_text[:400] + "\n...(kesildi)..."
        output += f"**Errors:**\n```\n{stderr_text}\n```\n"
        
    if not output:
        output = "Komut çalıştı ama herhangi bir çıktı üretmedi."

    # Embed oluştur
    color = discord.Color.green() if result["success"] else discord.Color.red()
    status = "✅ Başarılı" if result["success"] else "❌ Hata"
    
    embed = discord.Embed(
        title=f"{status}: {cmd[:50]}",
        description=output,
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Return Code: {result['return_code']}")
    
    await msg.edit(content=None, embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! Gecikme: {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("HATA: Lütfen config.py dosyasına Discord Bot Token'ınızı ekleyin!")
        sys.exit(1)
        
    try:
        bot.run(config.BOT_TOKEN)
    except Exception as e:
        print(f"Bot başlatılamadı: {e}")