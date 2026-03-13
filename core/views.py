import discord
from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
from Tools.Fun.panel import embed_fun_panel, FunPanelView
from Tools.System.panel import embed_system_panel, SystemPanelView
from Tools.Windows.panel import embed_windows_panel, WindowsPanelView


class StartupView(discord.ui.View):
    """View attached to the startup message with Tools, Fun, and System buttons."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tools", emoji="🧰", style=discord.ButtonStyle.primary)
    async def tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())

    @discord.ui.button(label="Fun", emoji="🎉", style=discord.ButtonStyle.danger)
    async def fun_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

    @discord.ui.button(label="System", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def system_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), view=SystemPanelView())

    @discord.ui.button(label="Windows", emoji="🪟", style=discord.ButtonStyle.success)
    async def windows_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_windows_panel(), view=WindowsPanelView())

