import discord
import ctypes
from ctypes import wintypes


def _get_tools_panel():
    from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
    return embed_tools_panel, ToolsPanelView


# ========================================
# Interactive ActiveWindows UI
# ========================================

class ActiveWindowsManager:
    """Helper class to enumerate visible windows using ctypes."""
    
    @staticmethod
    def get_windows():
        """Returns a list of dicts with 'title' and 'handle' for all visible windows."""
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        IsWindowVisible = user32.IsWindowVisible
        
        windows = []
        
        def callback(hwnd, lparam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value.strip()
                    if title:
                        windows.append({"title": title, "handle": hwnd})
            return True
        
        EnumWindows(EnumWindowsProc(callback), 0)
        return windows
    
    @staticmethod
    def close_window(hwnd: int):
        """Send WM_CLOSE to a window handle."""
        import ctypes
        WM_CLOSE = 0x0010
        try:
            ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            return True, "Window close signal sent."
        except Exception as e:
            return False, str(e)


def build_activewindows_embed(session_id: str, selected_idx: int = -1):
    """Build the ActiveWindows embed with a table-style layout."""
    windows = ActiveWindowsManager.get_windows()
    
    # Build table header
    header = f"{'[ ActiveWindow ]':<42} {'[ Handle ]':>10}"
    sep = "━" * 54
    
    # Build rows
    rows = ""
    for i, w in enumerate(windows):
        title = w['title']
        if len(title) > 38:
            title = title[:35] + "..."
        handle_str = str(w['handle'])
        
        # Mark selected row
        if i == selected_idx:
            marker = "►"
        else:
            marker = " "
        
        icon = "🪟"
        rows += f"{marker} {icon} {title:<38} {handle_str:>10}\n"
    
    if not windows:
        rows = "  (No visible windows found)\n"
    
    table_block = f"```\n{header}\n{sep}\n{rows}```"
    
    # Truncate if too long for embed
    if len(table_block) > 4000:
        table_block = table_block[:3990] + "\n...```"
    
    selected_count = 1 if selected_idx >= 0 else 0
    
    embed = discord.Embed(
        title=f"🪟 ActiveWindows : {session_id}",
        description=table_block,
        color=discord.Color.from_rgb(0, 120, 215)
    )
    embed.set_footer(text=f"Selected [{selected_count}]  Windows [{len(windows)}]")
    
    return embed, windows


class ActiveWindowsSelect(discord.ui.Select):
    """Dropdown to select a window from the list."""
    def __init__(self, windows: list, session_id: str):
        self.session_id = session_id
        self.windows_data = windows
        
        if windows:
            options = []
            for i, w in enumerate(windows[:25]):  # Discord max 25 options
                label = w['title'][:100] if len(w['title']) > 100 else w['title']
                options.append(discord.SelectOption(
                    label=label,
                    description=f"Handle: {w['handle']}",
                    value=str(i),
                    emoji="🪟"
                ))
        else:
            options = [discord.SelectOption(label="(no windows)", value="_none")]
        
        super().__init__(placeholder="🪟 Select a window...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return
        
        idx = int(selected)
        embed, windows = build_activewindows_embed(self.session_id, selected_idx=idx)
        view = ActiveWindowsView(self.session_id, selected_idx=idx)
        await interaction.response.edit_message(embed=embed, view=view)


class ActiveWindowsView(discord.ui.View):
    """Interactive view for ActiveWindows with Refresh and Close buttons."""
    def __init__(self, session_id: str, selected_idx: int = -1):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.selected_idx = selected_idx
        
        # Get current windows for the dropdown
        windows = ActiveWindowsManager.get_windows()
        self.windows_data = windows
        
        # Add select dropdown
        self.add_item(ActiveWindowsSelect(windows, session_id))
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed, windows = build_activewindows_embed(self.session_id)
        view = ActiveWindowsView(self.session_id)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Close", emoji="❌", style=discord.ButtonStyle.secondary, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_idx < 0 or self.selected_idx >= len(self.windows_data):
            await interaction.response.send_message("❌ Please select a window first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        target = self.windows_data[self.selected_idx]
        success, msg = ActiveWindowsManager.close_window(target['handle'])
        
        # After closing, refresh the window list in the same message
        embed, windows = build_activewindows_embed(self.session_id)
        
        # Add status info to embed
        if success:
            embed.add_field(name="✅ Closed", value=f"`{target['title']}`", inline=False)
        else:
            embed.add_field(name="❌ Failed", value=f"`{target['title']}` — {msg}", inline=False)
        
        view = ActiveWindowsView(self.session_id)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_get_tools_panel()[0](), view=_get_tools_panel()[1]())

