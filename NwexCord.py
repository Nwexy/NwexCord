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

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

class ShellExecutor:
    @staticmethod
    def execute(command: str):
        """Executes a system command and returns the output"""
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
    
    print(f'--- NwexCord Active ---')
    print(f'Bot Username: {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Server Count: {len(bot.guilds)}')
    print(f'Invite Link: {invite_link}')
    print(f'----------------------')
    
    if len(bot.guilds) == 0:
        print("WARNING: The bot is currently not in any servers!")
        print("Please use the link above to invite the bot to your server.")
    
    # Set bot status (Activity)
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name=f"{config.PREFIX}shell"
    ))
    
    # Send "Active" message to the first available channel
    sent_message = False
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(f"🚀 **NwexCord System Started!**\nWaiting for commands. Usage: `{config.PREFIX}shell <command>`")
                    sent_message = True
                    break
                except:
                    continue
        if sent_message: break

@bot.command(name="shell")
async def shell_command(ctx, *, cmd: str):
    """Executes command via Discord: .shell dir"""
    
    # Send info message
    msg = await ctx.send(f"⚡ Executing: `{cmd}`...")
    
    # Execute command
    result = ShellExecutor.execute(cmd)
    
    # Prepare output
    output = ""
    if result["stdout"]:
        # Discord has a 2000 character limit, taking the last 1500 characters
        stdout_text = result["stdout"]
        if len(stdout_text) > 1500:
            stdout_text = "...(truncated)...\n" + stdout_text[-1500:]
        output += f"**Output:**\n```\n{stdout_text}\n```\n"
        
    if result["stderr"]:
        stderr_text = result["stderr"]
        if len(stderr_text) > 400:
            stderr_text = stderr_text[:400] + "\n...(truncated)..."
        output += f"**Errors:**\n```\n{stderr_text}\n```\n"
        
    if not output:
        output = "Command executed but produced no output."

    # Create embed
    color = discord.Color.green() if result["success"] else discord.Color.red()
    status = "✅ Success" if result["success"] else "❌ Error"
    
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
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Please add your Discord Bot Token to config.py!")
        sys.exit(1)
        
    try:
        bot.run(config.BOT_TOKEN)
    except Exception as e:
        print(f"Failed to start bot: {e}")