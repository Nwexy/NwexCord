import discord
import subprocess
import os
import asyncio


def _get_tools_panel():
    from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
    return embed_tools_panel, ToolsPanelView


# ========================================
# Interactive Startup Manager UI
# ========================================

class StartupManager:
    """Helper class to gather startup items from 3 sources."""
    
    # Startup folder paths
    USER_STARTUP = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
    COMMON_STARTUP = os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup')
    
    # Registry Run keys
    REG_KEYS = [
        r'HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run',
        r'HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\RunOnce',
        r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
        r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
    ]
    
    @staticmethod
    def get_startup_files():
        """Get items from Startup folders."""
        items = []
        for folder in [StartupManager.USER_STARTUP, StartupManager.COMMON_STARTUP]:
            try:
                if os.path.isdir(folder):
                    for f in os.listdir(folder):
                        full_path = os.path.join(folder, f)
                        items.append({
                            'name': f,
                            'type': 'File',
                            'path': folder,
                            'full_path': full_path,
                            'source': 'file',
                            'icon': '📄'
                        })
            except Exception:
                pass
        return items
    
    @staticmethod
    def get_registry_entries():
        """Get startup entries from Registry Run keys."""
        items = []
        for key_path in StartupManager.REG_KEYS:
            try:
                result = subprocess.run(
                    f'reg query "{key_path}"',
                    shell=True, capture_output=True, text=True,
                    timeout=10, encoding='utf-8', errors='replace'
                )
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('HKEY') or line.startswith('End'):
                        continue
                    parts = line.split(None, 2)
                    if len(parts) >= 3:
                        items.append({
                            'name': parts[0],
                            'type': 'Registry',
                            'path': key_path,
                            'full_path': parts[2],
                            'source': 'registry',
                            'reg_key': key_path,
                            'reg_name': parts[0],
                            'icon': '🔑'
                        })
            except Exception:
                pass
        return items
    
    @staticmethod
    def get_scheduled_tasks():
        """Get startup-related scheduled tasks."""
        items = []
        try:
            # Get tasks that trigger on Boot or Logon
            cmd = "powershell \"Get-ScheduledTask | Where-Object { $_.Triggers.CimClass.CimClassName -match 'BootTrigger|LogonTrigger' } | Select-Object TaskPath, TaskName | Format-Table -HideTableHeaders\""
            result = subprocess.run(
                cmd,
                shell=True, capture_output=True, text=True,
                timeout=15, encoding='utf-8', errors='replace'
            )
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Output format: \Microsoft\Windows\AppID\    VerifiedPublisherCertStoreCheck
                # Split by space, first part is path, rest is name
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    task_path = parts[0].strip()
                    task_name = parts[1].strip()
                    full_task_name = f"{task_path}{task_name}" if task_path.endswith('\\') else f"{task_path}\\{task_name}"
                    
                    items.append({
                        'name': task_name,
                        'type': 'Task',
                        'path': task_path,
                        'full_path': full_task_name,
                        'source': 'task',
                        'task_name': full_task_name,
                        'icon': '⏰'
                    })
        except Exception:
            pass
        return items
    
    @staticmethod
    def get_all_items():
        """Gather startup items from all 3 sources."""
        items = []
        items.extend(StartupManager.get_startup_files())
        items.extend(StartupManager.get_registry_entries())
        items.extend(StartupManager.get_scheduled_tasks())
        return items
    
    @staticmethod
    def remove_item(item: dict):
        """Remove a startup item based on its source."""
        try:
            if item['source'] == 'file':
                path = item['full_path']
                if os.path.isfile(path):
                    os.remove(path)
                    return True, f"File deleted: {item['name']}"
                elif os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path)
                    return True, f"Folder deleted: {item['name']}"
                else:
                    return False, "File not found."
            
            elif item['source'] == 'registry':
                result = subprocess.run(
                    f'reg delete "{item["reg_key"]}" /v "{item["reg_name"]}" /f',
                    shell=True, capture_output=True, text=True,
                    timeout=10, encoding='utf-8', errors='replace'
                )
                if result.returncode == 0:
                    return True, f"Registry value deleted: {item['name']}"
                return False, result.stderr.strip() or "Failed to delete registry value."
            
            elif item['source'] == 'task':
                result = subprocess.run(
                    f'schtasks /delete /tn "{item["task_name"]}" /f',
                    shell=True, capture_output=True, text=True,
                    timeout=10, encoding='utf-8', errors='replace'
                )
                if result.returncode == 0:
                    return True, f"Task deleted: {item['name']}"
                return False, result.stderr.strip() or "Failed to delete task."
            
            return False, "Unknown source type."
        except Exception as e:
            return False, str(e)


def build_startup_embed(session_id: str, items: list = None, selected_idx: int = -1):
    """Build the Startup Manager embed with table-style layout."""
    if items is None:
        items = StartupManager.get_all_items()
    
    # Build table header
    header = f"{'[ Name ]':<38} {'[ Type ]':<10} {'[ Path ]'}"
    sep = "━" * 72
    
    rows = ""
    for i, item in enumerate(items):
        name = item['name']
        if len(name) > 34:
            name = name[:31] + "..."
        
        path_display = item['path']
        if len(path_display) > 38:
            path_display = path_display[:35] + "..."
        
        marker = "►" if i == selected_idx else " "
        icon = item['icon']
        item_type = item['type']
        
        rows += f"{marker} {icon} {name:<34} {item_type:<8} {path_display}\n"
    
    if not items:
        rows = "  (No startup items found)\n"
    
    table_block = f"```\n{header}\n{sep}\n{rows}```"
    
    if len(table_block) > 4000:
        table_block = table_block[:3990] + "\n...```"
    
    selected_count = 1 if selected_idx >= 0 else 0
    
    embed = discord.Embed(
        title=f"🚀 Startup Manager : {session_id}",
        description=table_block,
        color=discord.Color.from_rgb(0, 120, 215)
    )
    embed.set_footer(text=f"Selected [{selected_count}]  Startup [{len(items)}]")
    
    return embed, items


class StartupSelect(discord.ui.Select):
    """Dropdown to select a startup item from the list."""
    def __init__(self, items: list, session_id: str):
        self.session_id = session_id
        self.items_data = items
        
        if items:
            options = []
            for i, item in enumerate(items[:25]):  # Discord max 25 options
                label = item['name'][:100] if len(item['name']) > 100 else item['name']
                desc = f"{item['type']} — {item['path']}"
                options.append(discord.SelectOption(
                    label=label,
                    description=desc[:100],
                    value=str(i),
                    emoji=item['icon']
                ))
        else:
            options = [discord.SelectOption(label="(no items)", value="_none")]
        
        super().__init__(placeholder="🚀 Select a startup item...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return
        
        idx = int(selected)
        embed, items = build_startup_embed(self.session_id, self.items_data, selected_idx=idx)
        view = StartupManagerView(self.session_id, self.items_data, selected_idx=idx)
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class StartupManagerView(discord.ui.View):
    """Interactive view for Startup Manager with Remove, Refresh, and Back."""
    def __init__(self, session_id: str, items: list = None, selected_idx: int = -1):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.selected_idx = selected_idx
        self.items_data = items if items is not None else StartupManager.get_all_items()
        
        # Add select dropdown
        self.add_item(StartupSelect(self.items_data, session_id))
    
    @discord.ui.button(label="Remove", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_idx < 0 or self.selected_idx >= len(self.items_data):
            await interaction.response.send_message("❌ Please select a startup item first!", ephemeral=True)
            return
        
        await interaction.response.defer()
        target = self.items_data[self.selected_idx]
        success, msg = StartupManager.remove_item(target)
        
        # After removing, refresh the list
        new_items = StartupManager.get_all_items()
        embed, items = build_startup_embed(self.session_id, new_items)
        
        if success:
            embed.add_field(name="✅ Removed", value=f"`{target['name']}` ({target['type']})", inline=False)
        else:
            embed.add_field(name="❌ Failed", value=f"`{target['name']}` — {msg}", inline=False)
        
        view = StartupManagerView(self.session_id, new_items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        new_items = StartupManager.get_all_items()
        embed, items = build_startup_embed(self.session_id, new_items)
        view = StartupManagerView(self.session_id, new_items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


# ========================================
# Interactive Process Manager UI
# ========================================

