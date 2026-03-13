import discord
import subprocess
import os
import asyncio
import ctypes


def _get_tools_panel():
    from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
    return embed_tools_panel, ToolsPanelView


class ProcessManager:
    """Helper class to get process data and manage processes."""
    
    @staticmethod
    def get_processes():
        """Get list of running processes with Name, PID, Description."""
        try:
            cmd = 'powershell "Get-Process | Select-Object ProcessName, Id, Description | Sort-Object ProcessName | Format-Table -HideTableHeaders"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=15, encoding='utf-8', errors='replace'
            )
            processes = []
            seen = set()
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(None, 2)
                if len(parts) >= 2:
                    name = parts[0].strip()
                    try:
                        pid = int(parts[1].strip())
                    except ValueError:
                        continue
                    desc = parts[2].strip() if len(parts) >= 3 else ""
                    key = f"{name}_{pid}"
                    if key not in seen:
                        seen.add(key)
                        processes.append({
                            'name': f"{name}.exe",
                            'pid': pid,
                            'description': desc if desc else name,
                        })
            return processes
        except Exception:
            return []
    
    @staticmethod
    def close_process(pid: int):
        """Kill a process by PID."""
        try:
            result = subprocess.run(
                f'taskkill /F /PID {pid}',
                shell=True, capture_output=True, text=True,
                timeout=10, encoding='utf-8', errors='replace'
            )
            if result.returncode == 0:
                return True, "Process terminated."
            return False, result.stderr.strip() or "Failed to terminate."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def restart_process(pid: int, name: str):
        """Kill and restart a process."""
        try:
            # First get the executable path
            cmd = f'powershell "(Get-Process -Id {pid}).Path"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=10, encoding='utf-8', errors='replace'
            )
            exe_path = result.stdout.strip()
            
            if not exe_path or not os.path.exists(exe_path):
                return False, "Could not find executable path."
            
            # Kill the process
            subprocess.run(f'taskkill /F /PID {pid}', shell=True, timeout=10)
            
            # Start it again
            subprocess.Popen(exe_path, shell=True)
            return True, f"Process restarted: {name}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def suspend_process(pid: int):
        """Suspend a process using PowerShell."""
        try:
            cmd = f'powershell "(Get-Process -Id {pid}).Suspend()"'
            # Use pssuspend alternative via debug API
            cmd = f'powershell "$proc = Get-Process -Id {pid}; $proc.Suspend()"'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=10, encoding='utf-8', errors='replace'
            )
            # Suspend via NtSuspendProcess
            import ctypes
            PROCESS_SUSPEND_RESUME = 0x0800
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
            if handle:
                ntdll = ctypes.windll.ntdll
                ntdll.NtSuspendProcess(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                return True, "Process suspended."
            return False, "Could not open process."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def resume_process(pid: int):
        """Resume a suspended process."""
        try:
            import ctypes
            PROCESS_SUSPEND_RESUME = 0x0800
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
            if handle:
                ntdll = ctypes.windll.ntdll
                ntdll.NtResumeProcess(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                return True, "Process resumed."
            return False, "Could not open process."
        except Exception as e:
            return False, str(e)


def build_process_embed(session_id: str, page: int = 0, processes: list = None, selected_idx: int = -1):
    """Build the Process Manager embed with table-style layout and pagination."""
    if processes is None:
        processes = ProcessManager.get_processes()
        
    per_page = 20
    total = len(processes)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    
    start = page * per_page
    end = min(start + per_page, total)
    page_procs = processes[start:end]
    
    # Build table header
    header = f"{'[ Name ]':<28} {'[ PID ]':<8} {'[ Description ]'}"
    sep = "\u2501" * 64
    
    rows = ""
    for i, proc in enumerate(page_procs):
        name = proc['name']
        if len(name) > 24:
            name = name[:21] + "..."
        
        desc = proc['description']
        if len(desc) > 24:
            desc = desc[:21] + "..."
        
        overall_idx = start + i
        marker = "\u25ba" if overall_idx == selected_idx else " "
        pid_str = str(proc['pid'])
        
        rows += f"{marker} {name:<26} {pid_str:<6} {desc}\n"
    
    if not processes:
        rows = "  (No processes found)\n"
    
    table_block = f"```\n{header}\n{sep}\n{rows}```"
    
    if len(table_block) > 4000:
        table_block = table_block[:3990] + "\n...```"
    
    selected_count = 1 if selected_idx >= 0 else 0
    
    embed = discord.Embed(
        title=f"\ud83d\udcca Process Manager : {session_id}",
        description=table_block,
        color=discord.Color.from_rgb(0, 120, 215)
    )
    embed.set_footer(text=f"Page [{page+1}/{total_pages}]  Selected [{selected_count}]  Process [{total}]")
    
    return embed, processes, page, total_pages


class ProcessSelect(discord.ui.Select):
    """Dropdown to select a process from the current page."""
    def __init__(self, session_id: str, page: int, processes: list):
        self.session_id = session_id
        self.page = page
        self.processes_data = processes
        
        per_page = 20
        start = page * per_page
        end = min(start + per_page, len(processes))
        page_procs = processes[start:end]
        
        if page_procs:
            options = []
            for i, proc in enumerate(page_procs):
                overall_idx = start + i
                label = f"{proc['name']} (PID: {proc['pid']})"
                label = label[:100]
                options.append(discord.SelectOption(
                    label=label,
                    description=proc['description'][:100] if proc['description'] else "No description",
                    value=str(overall_idx),
                    emoji="\ud83d\udcca"
                ))
        else:
            options = [discord.SelectOption(label="(no processes)", value="_none")]
        
        super().__init__(placeholder="\ud83d\udcca Select a process...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return
        
        idx = int(selected)
        embed, procs, pg, tp = build_process_embed(self.session_id, self.page, self.processes_data, selected_idx=idx)
        view = ProcessManagerView(self.session_id, pg, self.processes_data, selected_idx=idx)
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class ProcessManagerView(discord.ui.View):
    """Interactive view for Process Manager with Refresh, Close, Restart, Suspend, Resume."""
    def __init__(self, session_id: str, page: int = 0, processes: list = None, selected_idx: int = -1):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.page = page
        self.selected_idx = selected_idx
        self.processes_data = processes if processes is not None else ProcessManager.get_processes()
        self.total_pages = max(1, (len(self.processes_data) + 19) // 20)
        
        # Add select dropdown
        self.add_item(ProcessSelect(session_id, page, self.processes_data))
    
    def _get_selected(self):
        """Get the selected process or None."""
        if self.selected_idx < 0 or self.selected_idx >= len(self.processes_data):
            return None
        return self.processes_data[self.selected_idx]
    
    @discord.ui.button(label="\u25c0", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = max(0, self.page - 1)
        embed, procs, pg, tp = build_process_embed(self.session_id, new_page, self.processes_data)
        view = ProcessManagerView(self.session_id, pg, self.processes_data)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="\u25b6", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = min(self.total_pages - 1, self.page + 1)
        embed, procs, pg, tp = build_process_embed(self.session_id, new_page, self.processes_data)
        view = ProcessManagerView(self.session_id, pg, self.processes_data)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Refresh", emoji="\ud83d\udd04", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        new_procs = ProcessManager.get_processes()
        embed, procs, pg, tp = build_process_embed(self.session_id, 0, new_procs)
        view = ProcessManagerView(self.session_id, 0, new_procs)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Close", emoji="\ud83d\udeab", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        success, msg = ProcessManager.close_process(target['pid'])
        new_procs = ProcessManager.get_processes()
        
        per_page = 20
        total = len(new_procs)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(self.page, total_pages - 1))
        
        embed, procs, pg, tp = build_process_embed(self.session_id, page, new_procs)
        
        if success:
            embed.add_field(name="\u2705 Closed", value=f"`{target['name']}` (PID: {target['pid']})", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = ProcessManagerView(self.session_id, pg, new_procs)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Restart", emoji="\ud83d\udd04", style=discord.ButtonStyle.primary, row=2)
    async def restart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        success, msg = ProcessManager.restart_process(target['pid'], target['name'])
        new_procs = ProcessManager.get_processes()
        
        per_page = 20
        total = len(new_procs)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(self.page, total_pages - 1))
        
        embed, procs, pg, tp = build_process_embed(self.session_id, page, new_procs)
        
        if success:
            embed.add_field(name="\u2705 Restarted", value=f"`{target['name']}` (PID: {target['pid']})", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = ProcessManagerView(self.session_id, pg, new_procs)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Suspend", emoji="\u23f8", style=discord.ButtonStyle.secondary, row=2)
    async def suspend_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        success, msg = ProcessManager.suspend_process(target['pid'])
        embed, procs, pg, tp = build_process_embed(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        
        if success:
            embed.add_field(name="\u23f8 Suspended", value=f"`{target['name']}` (PID: {target['pid']})", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = ProcessManagerView(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Resume", emoji="\u25b6", style=discord.ButtonStyle.secondary, row=2)
    async def resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        success, msg = ProcessManager.resume_process(target['pid'])
        embed, procs, pg, tp = build_process_embed(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        
        if success:
            embed.add_field(name="\u25b6 Resumed", value=f"`{target['name']}` (PID: {target['pid']})", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = ProcessManagerView(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="\u2b05", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


# ========================================
# Interactive Installed Programs UI
# ========================================

