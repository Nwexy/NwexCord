import discord
import subprocess
import asyncio


def _get_tools_panel():
    from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
    return embed_tools_panel, ToolsPanelView


class InstalledProgramsManager:
    """Helper class to get installed programs and uninstall them."""
    
    REG_PATHS = [
        r'HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall',
        r'HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
        r'HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall',
    ]
    
    @staticmethod
    def get_programs():
        """Get list of installed programs from registry."""
        programs = []
        seen = set()
        for reg_path in InstalledProgramsManager.REG_PATHS:
            try:
                cmd = f'powershell "Get-ItemProperty \'Registry::{reg_path}\\*\' -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -ne $null }} | Select-Object DisplayName, UninstallString | Sort-Object DisplayName | Format-Table -HideTableHeaders"'
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=15, encoding='utf-8', errors='replace'
                )
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    # Split into name and uninstall string
                    parts = line.split(None, 1)
                    if len(parts) >= 1:
                        # The name may contain spaces, so we need a smarter approach
                        # Use the full line as it may be just the name
                        name = line.strip()
                        if name and name not in seen:
                            seen.add(name)
                            programs.append({
                                'name': name,
                            })
            except Exception:
                pass
        
        # Sort alphabetically
        programs.sort(key=lambda p: p['name'].lower())
        return programs
    
    @staticmethod
    def uninstall_program(name: str):
        """Attempt to uninstall a program by finding its UninstallString."""
        try:
            for reg_path in InstalledProgramsManager.REG_PATHS:
                cmd = f"powershell \"Get-ItemProperty 'Registry::{reg_path}\\*' -ErrorAction SilentlyContinue | Where-Object {{ $_.DisplayName -eq '{name}' }} | Select-Object -ExpandProperty UninstallString\""
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=10, encoding='utf-8', errors='replace'
                )
                uninstall_str = result.stdout.strip()
                if uninstall_str:
                    # Execute uninstall command
                    subprocess.Popen(uninstall_str, shell=True)
                    return True, f"Uninstall started for: {name}"
            return False, "Uninstall string not found."
        except Exception as e:
            return False, str(e)


def build_programs_embed(session_id: str, page: int = 0, programs: list = None, selected_idx: int = -1):
    """Build the Installed Programs embed with table-style layout and pagination."""
    if programs is None:
        programs = InstalledProgramsManager.get_programs()
    
    per_page = 15
    total = len(programs)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    
    start = page * per_page
    end = min(start + per_page, total)
    page_progs = programs[start:end]
    
    # Build table header
    header = "[ Name ]"
    sep = "\u2501" * 54
    
    rows = ""
    for i, prog in enumerate(page_progs):
        overall_idx = start + i
        name = prog['name']
        if len(name) > 50:
            name = name[:47] + "..."
        
        marker = "\u25ba" if overall_idx == selected_idx else " "
        rows += f"{marker} \ud83d\udce6 {name}\n"
    
    if not programs:
        rows = "  (No programs found)\n"
    
    table_block = f"```\n{header}\n{sep}\n{rows}```"
    
    if len(table_block) > 4000:
        table_block = table_block[:3990] + "\n...```"
    
    selected_count = 1 if selected_idx >= 0 else 0
    
    embed = discord.Embed(
        title=f"\ud83d\udcbf Installed Programs : {session_id[:16]}...",
        description=table_block,
        color=discord.Color.from_rgb(0, 120, 215)
    )
    embed.set_footer(text=f"Page [{page+1}/{total_pages}]  Selected [{selected_count}]  Installed [{total}]")
    
    return embed, programs, page, total_pages


class ProgramsSelect(discord.ui.Select):
    """Dropdown to select a program from the current page."""
    def __init__(self, session_id: str, page: int, programs: list):
        self.session_id = session_id
        self.page = page
        self.programs_data = programs
        
        per_page = 15
        start = page * per_page
        end = min(start + per_page, len(programs))
        page_progs = programs[start:end]
        
        if page_progs:
            options = []
            for i, prog in enumerate(page_progs):
                overall_idx = start + i
                label = prog['name'][:100]
                options.append(discord.SelectOption(
                    label=label,
                    value=str(overall_idx),
                    emoji="\ud83d\udce6"
                ))
        else:
            options = [discord.SelectOption(label="(no programs)", value="_none")]
        
        super().__init__(placeholder="\ud83d\udcbf Select a program...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return
        
        idx = int(selected)
        embed, progs, pg, tp = build_programs_embed(self.session_id, self.page, self.programs_data, selected_idx=idx)
        view = InstalledProgramsView(self.session_id, pg, self.programs_data, selected_idx=idx)
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class InstalledProgramsView(discord.ui.View):
    """Interactive view for Installed Programs with Refresh, Uninstall, pagination."""
    def __init__(self, session_id: str, page: int = 0, programs: list = None, selected_idx: int = -1):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.page = page
        self.selected_idx = selected_idx
        self.programs_data = programs if programs is not None else InstalledProgramsManager.get_programs()
        self.total_pages = max(1, (len(self.programs_data) + 14) // 15)
        
        # Add select dropdown
        self.add_item(ProgramsSelect(session_id, page, self.programs_data))
    
    @discord.ui.button(label="\u25c0", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = max(0, self.page - 1)
        embed, progs, pg, tp = build_programs_embed(self.session_id, new_page, self.programs_data)
        view = InstalledProgramsView(self.session_id, pg, self.programs_data)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="\u25b6", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = min(self.total_pages - 1, self.page + 1)
        embed, progs, pg, tp = build_programs_embed(self.session_id, new_page, self.programs_data)
        view = InstalledProgramsView(self.session_id, pg, self.programs_data)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Refresh", emoji="\ud83d\udd04", style=discord.ButtonStyle.secondary, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        new_progs = InstalledProgramsManager.get_programs()
        embed, progs, pg, tp = build_programs_embed(self.session_id, 0, new_progs)
        view = InstalledProgramsView(self.session_id, 0, new_progs)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Uninstall", emoji="\ud83d\udeab", style=discord.ButtonStyle.secondary, row=1)
    async def uninstall_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_idx < 0 or self.selected_idx >= len(self.programs_data):
            await interaction.response.send_message("\u274c Please select a program first!", ephemeral=True)
            return
        
        target = self.programs_data[self.selected_idx]
        success, msg = InstalledProgramsManager.uninstall_program(target['name'])
        
        embed, progs, pg, tp = build_programs_embed(self.session_id, self.page, self.programs_data)
        
        if success:
            embed.add_field(name="\u2705 Uninstall", value=f"`{target['name']}`", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = InstalledProgramsView(self.session_id, self.page, self.programs_data)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="\u2b05", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_get_tools_panel()[0](), view=_get_tools_panel()[1]())


# ========================================
# Fun Panel
# ========================================

