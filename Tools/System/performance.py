import discord
import asyncio
from Tools.System.manager import SystemManager


def _progress_bar(percent, length=10):
    """Create a text-based progress bar."""
    if isinstance(percent, str):
        return '░' * length
    filled = int(length * percent / 100)
    bar = '█' * filled + '░' * (length - filled)
    return bar


def build_performance_embed(session_id: str, data: dict = None):
    """Build the Performance embed similar to the reference image."""
    if data is None:
        data = SystemManager.get_performance()

    cpu_pct = data.get('cpu_percent', 'N/A')
    ram_pct = data.get('ram_percent', 'N/A')

    cpu_bar = _progress_bar(cpu_pct)
    ram_bar = _progress_bar(ram_pct)

    cpu_pct_str = f"{cpu_pct}%" if isinstance(cpu_pct, (int, float)) else cpu_pct
    ram_pct_str = f"{ram_pct}%" if isinstance(ram_pct, (int, float)) else ram_pct

    embed = discord.Embed(
        title=f"⚡ Performance : {session_id}",
        color=discord.Color.from_rgb(0, 120, 215)
    )

    # CPU Section
    cpu_info = (
        f"**CPU :** {data.get('cpu_name', 'Unknown')}\n\n"
        f"```\n"
        f"  Usage    [{cpu_bar}] {cpu_pct_str}\n"
        f"```\n"
        f"🟩 **Speed** : {data.get('cpu_speed', 'N/A')}\n"
        f"🟩 **Cores** : {data.get('cpu_count_physical', 'N/A')}\n"
        f"🟩 **Logical** : {data.get('cpu_count_logical', 'N/A')}"
    )
    embed.add_field(name="🧠 CPU", value=cpu_info, inline=False)

    # RAM Section
    ram_info = (
        f"**RAM :** {data.get('ram_total', 'Unknown')}\n\n"
        f"```\n"
        f"  Usage    [{ram_bar}] {ram_pct_str}\n"
        f"```\n"
        f"🟧 **Speed** : {data.get('ram_speed', 'N/A')}\n"
        f"🟧 **Used** : {data.get('ram_used', 'N/A')}\n"
        f"🟧 **Free** : {data.get('ram_free', 'N/A')}"
    )
    embed.add_field(name="💾 RAM", value=ram_info, inline=False)

    # Uptime
    embed.add_field(
        name="⏱️ SystemUpTime",
        value=f"🕐 **{data.get('uptime', 'N/A')}**",
        inline=False
    )

    embed.set_footer(text=f"NwexCord • Performance Monitor")
    return embed


class PerformanceView(discord.ui.View):
    """Interactive view for Performance with Stop (refresh toggle) and Back."""
    def __init__(self, session_id: str = ""):
        super().__init__(timeout=300)
        self.session_id = session_id

    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, SystemManager.get_performance)
        embed = build_performance_embed(self.session_id, data)
        await interaction.edit_original_response(content=None, embed=embed, view=PerformanceView(self.session_id))

    @discord.ui.button(label="Back to System", emoji="⬅", style=discord.ButtonStyle.secondary, row=0)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), view=SystemPanelView())


