import discord
import subprocess
import asyncio
import os
import re
import hashlib


def _get_tools_panel():
    from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
    return embed_tools_panel, ToolsPanelView


# ========================================
# Interactive Registry Editor
# ========================================

import hashlib

ROOT_HIVES = [
    "HKEY_CLASSES_ROOT",
    "HKEY_CURRENT_USER",
    "HKEY_LOCAL_MACHINE",
    "HKEY_USERS",
]

class RegistryEditor:
    """Helper class to interact with the Windows Registry via reg.exe."""
    
    @staticmethod
    def get_subkeys(path: str):
        """Get subkeys of a registry path."""
        try:
            result = subprocess.run(
                f'reg query "{path}"', shell=True,
                capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            subkeys = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line and line.startswith(path + "\\"):
                    subkey_name = line[len(path)+1:]
                    if "\\" not in subkey_name:
                        subkeys.append(subkey_name)
            return subkeys
        except:
            return []
    
    @staticmethod
    def get_values(path: str):
        """Get values (name, type, data) of a registry key."""
        try:
            result = subprocess.run(
                f'reg query "{path}" /v *', shell=True,
                capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            values = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith("HKEY") or line.startswith("End"):
                    continue
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    values.append({
                        "name": parts[0],
                        "type": parts[1],
                        "data": parts[2]
                    })
                elif len(parts) == 2:
                    values.append({
                        "name": parts[0],
                        "type": parts[1],
                        "data": ""
                    })
            return values
        except:
            return []
    
    @staticmethod
    def add_value(path: str, name: str, reg_type: str, data: str):
        """Add or set a registry value."""
        try:
            result = subprocess.run(
                f'reg add "{path}" /v "{name}" /t {reg_type} /d "{data}" /f',
                shell=True, capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def delete_value(path: str, name: str):
        """Delete a registry value."""
        try:
            if name.lower() == "(default)":
                cmd = f'reg delete "{path}" /ve /f'
            else:
                cmd = f'reg delete "{path}" /v "{name}" /f'
            result = subprocess.run(
                cmd,
                shell=True, capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            return result.returncode == 0, result.stdout.strip() + result.stderr.strip()
        except Exception as e:
            return False, str(e)


def build_registry_embed(current_path: str, session_id: str):
    """Build the registry editor embed for a given path."""
    parts = current_path.split("\\") if current_path else []
    
    # Build tree view
    tree = ""
    if not current_path:
        for hive in ROOT_HIVES:
            tree += f"  📁 {hive}\n"
    else:
        for i, part in enumerate(parts):
            prefix = "┣ " if i < len(parts) - 1 else "┗ "
            indent = "┃ " * i
            icon = "📂" if i == len(parts) - 1 else "📁"
            bold = f"**{part}**" if i == len(parts) - 1 else part
            tree += f"{indent}{prefix}{icon} {bold}\n"
        
        subkeys = RegistryEditor.get_subkeys(current_path)
        indent = "┃ " * len(parts)
        for sk in subkeys[:12]:
            tree += f"{indent}┣ 📁 {sk}\n"
        if len(subkeys) > 12:
            tree += f"{indent}┗ *...+{len(subkeys)-12} more*\n"
    
    # Build values table as a monospace code block
    values_block = ""
    val_count = 0
    if current_path:
        values = RegistryEditor.get_values(current_path)
        val_count = len(values)
        if values:
            # Calculate column widths
            names = [v['name'][:18] for v in values[:10]]
            types = [v['type'][:14] for v in values[:10]]
            datas = [v['data'][:22] for v in values[:10]]
            
            nw = max(max(len(n) for n in names), 4) + 1
            tw = max(max(len(t) for t in types), 4) + 1
            
            header = f"{'Name':<{nw}} {'Type':<{tw}} Value"
            sep = "─" * (nw + tw + 20)
            values_block = f"```\n{header}\n{sep}\n"
            
            for i in range(len(names)):
                values_block += f"{names[i]:<{nw}} {types[i]:<{tw}} {datas[i]}\n"
            
            if val_count > 10:
                values_block += f"... +{val_count - 10} more values\n"
            values_block += "```"
        else:
            values_block = "```\nNo values in this key.\n```"
    else:
        values_block = "```\nSelect a hive to view values.\n```"
    
    subkey_count = len(RegistryEditor.get_subkeys(current_path)) if current_path else len(ROOT_HIVES)
    
    embed = discord.Embed(
        title=f"🔑 Registry Editor : {session_id[:20]}",
        color=discord.Color.from_rgb(30, 30, 30)
    )
    embed.add_field(name="🗂️ Tree", value=tree[:1024] if tree else "Empty", inline=False)
    embed.add_field(name=f"📄 Values [{val_count}]", value=values_block[:1024], inline=False)
    embed.set_footer(text=f"Keys [{subkey_count}] | Path: {current_path or 'Root'}")
    
    return embed


class NewValueModal(discord.ui.Modal, title="Add New Registry Value"):
    """Modal for adding a new registry value."""
    val_name = discord.ui.TextInput(label="Value Name", placeholder="MyValue", required=True)
    val_type = discord.ui.TextInput(label="Type", placeholder="REG_SZ, REG_DWORD, REG_QWORD...", default="REG_SZ", required=True)
    val_data = discord.ui.TextInput(label="Data", placeholder="Enter value data", required=True)
    
    def __init__(self, reg_path: str, session_id: str, page: int = 0):
        super().__init__()
        self.reg_path = reg_path
        self.session_id = session_id
        self.page = page
    
    async def on_submit(self, interaction: discord.Interaction):
        success, msg = RegistryEditor.add_value(
            self.reg_path, str(self.val_name), str(self.val_type), str(self.val_data)
        )
        status = "✅ Value added!" if success else f"❌ Error: {msg}"
        embed = build_registry_embed(self.reg_path, self.session_id)
        view = RegistryView(self.reg_path, self.session_id, page=self.page)
        await interaction.response.edit_message(content=status, embed=embed, view=view)


class EditValueModal(discord.ui.Modal, title="Edit Registry Value"):
    """Modal for editing a registry value (pre-filled)."""
    val_name = discord.ui.TextInput(label="Value Name", required=True)
    val_type = discord.ui.TextInput(label="Type", placeholder="REG_SZ, REG_DWORD...", default="REG_SZ", required=True)
    val_data = discord.ui.TextInput(label="New Data", placeholder="New value data", required=True)
    
    def __init__(self, reg_path: str, session_id: str, prefill_name: str = "", prefill_type: str = "REG_SZ", prefill_data: str = "", page: int = 0):
        super().__init__()
        self.reg_path = reg_path
        self.session_id = session_id
        self.page = page
        self.original_name = prefill_name  # Store original name to detect renames
        self.val_name.default = prefill_name
        self.val_type.default = prefill_type
        self.val_data.default = prefill_data[:100]
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_name = str(self.val_name).strip()
            reg_type = str(self.val_type).strip().upper()
            data = str(self.val_data).strip()
            
            # If name changed, delete old value first
            renamed = new_name != self.original_name
            if renamed:
                RegistryEditor.delete_value(self.reg_path, self.original_name)
            
            success, msg = RegistryEditor.add_value(self.reg_path, new_name, reg_type, data)
            
            color = discord.Color.green() if success else discord.Color.red()
            status_icon = "✅" if success else "❌"
            
            desc = f"**Name:** `{new_name}`\n**Type:** `{reg_type}`\n**Data:** `{data}`\n\n**Result:** {msg}"
            if renamed:
                desc = f"**Renamed:** `{self.original_name}` → `{new_name}`\n" + desc
            
            result_embed = discord.Embed(
                title=f"{status_icon} Edit Value",
                description=desc,
                color=color
            )
            result_embed.set_footer(text=f"Path: {self.reg_path}")
            await interaction.response.send_message(embed=result_embed, ephemeral=True)
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ Unexpected error: {e}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        try:
            await interaction.response.send_message(f"❌ Modal error: {error}", ephemeral=True)
        except Exception:
            await interaction.followup.send(f"❌ Modal error: {error}", ephemeral=True)


class RegistryNavSelect(discord.ui.Select):
    """Dropdown to navigate into subkeys (paginated, 24 per page)."""
    def __init__(self, current_path: str, session_id: str, page: int = 0):
        self.current_path = current_path
        self.session_id = session_id
        self.page = page
        
        if not current_path:
            options = [discord.SelectOption(label=h, emoji="📁") for h in ROOT_HIVES]
        else:
            all_subkeys = RegistryEditor.get_subkeys(current_path)
            start = page * 24
            end = start + 24
            page_keys = all_subkeys[start:end]
            total_pages = max(1, (len(all_subkeys) + 23) // 24)
            
            if page_keys:
                options = [discord.SelectOption(label=sk[:100], emoji="📁") for sk in page_keys]
                if total_pages > 1:
                    options.append(discord.SelectOption(
                        label=f"Page {page+1}/{total_pages} ({len(all_subkeys)} keys)",
                        value="_pageinfo", emoji="📄"
                    ))
            else:
                options = [discord.SelectOption(label="(no subkeys)", value="_none")]
        
        super().__init__(placeholder="📂 Navigate to subkey...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected in ("_none", "_pageinfo"):
            await interaction.response.defer()
            return
        new_path = f"{self.current_path}\\{selected}" if self.current_path else selected
        embed = build_registry_embed(new_path, self.session_id)
        view = RegistryView(new_path, self.session_id, page=0)
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class RegistryValSelect(discord.ui.Select):
    """Dropdown to select a value for viewing/editing/deleting."""
    def __init__(self, current_path: str, session_id: str, page: int = 0):
        self.current_path = current_path
        self.session_id = session_id
        self.page = page
        
        values = RegistryEditor.get_values(current_path) if current_path else []
        if values:
            options = []
            seen_values = set()
            for i, v in enumerate(values[:25]):
                data_preview = (v['data'][:45] if v['data'] else "(empty)")
                # Use index prefix to guarantee unique option values
                unique_val = f"{i}:{v['name'][:95]}"
                seen_values.add(unique_val)
                options.append(discord.SelectOption(
                    label=v['name'][:100],
                    description=f"{v['type']} = {data_preview}"[:100],
                    value=unique_val,
                    emoji="📝"
                ))
        else:
            options = [discord.SelectOption(label="(no values)", value="_none")]
        
        super().__init__(placeholder="📝 Select a value to manage...", options=options, row=1)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return
        
        # Parse index from unique value "idx:name"
        idx_str, val_name = selected.split(":", 1)
        idx = int(idx_str)
        
        values = RegistryEditor.get_values(self.current_path)
        found = values[idx] if idx < len(values) else None
        
        if not found:
            await interaction.response.send_message("❌ Value not found.", ephemeral=True)
            return
        
        detail_embed = discord.Embed(
            title=f"📝 Value: {found['name']}",
            color=discord.Color.from_rgb(50, 50, 80)
        )
        detail_embed.add_field(name="Name", value=f"`{found['name']}`", inline=True)
        detail_embed.add_field(name="Type", value=f"`{found['type']}`", inline=True)
        detail_embed.add_field(name="Data", value=f"```\n{found['data'][:500]}\n```", inline=False)
        detail_embed.set_footer(text=f"Path: {self.current_path}")
        
        view = ValueActionView(self.current_path, self.session_id, found['name'], found['type'], found['data'], self.page)
        await interaction.response.send_message(embed=detail_embed, view=view)


class ValueActionView(discord.ui.View):
    """Edit/Delete buttons shown after selecting a specific value."""
    def __init__(self, reg_path: str, session_id: str, val_name: str, val_type: str, val_data: str, page: int = 0):
        super().__init__(timeout=120)
        self.reg_path = reg_path
        self.session_id = session_id
        self.val_name = val_name
        self.val_type = val_type
        self.val_data = val_data
        self.page = page
    
    @discord.ui.button(label="Edit Value", emoji="✏️", style=discord.ButtonStyle.primary)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditValueModal(
            self.reg_path, self.session_id,
            prefill_name=self.val_name,
            prefill_type=self.val_type,
            prefill_data=self.val_data,
            page=self.page
        )
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Delete Value", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, msg = RegistryEditor.delete_value(self.reg_path, self.val_name)
        status = "✅ Value deleted!" if success else f"❌ Error: {msg}"
        result_embed = discord.Embed(
            title="🗑️ Delete Result",
            description=status,
            color=discord.Color.green() if success else discord.Color.red()
        )
        await interaction.response.edit_message(embed=result_embed, view=None)


class RegistryView(discord.ui.View):
    """Full interactive registry editor view with pagination and value selection."""
    def __init__(self, current_path: str = "", session_id: str = "", page: int = 0):
        super().__init__(timeout=300)
        self.current_path = current_path
        self.session_id = session_id
        self.page = page
        
        # Row 0: subkey navigation
        self.add_item(RegistryNavSelect(current_path, session_id, page))
        
        # Row 1: values dropdown (only when values exist)
        if current_path:
            vals = RegistryEditor.get_values(current_path)
            if vals:
                self.add_item(RegistryValSelect(current_path, session_id, page))
    
    @discord.ui.button(label="⬆ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.current_path or "\\" not in self.current_path:
            new_path = ""
        else:
            new_path = "\\".join(self.current_path.split("\\")[:-1])
        embed = build_registry_embed(new_path, self.session_id)
        view = RegistryView(new_path, self.session_id, page=0)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=2)
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = max(0, self.page - 1)
        embed = build_registry_embed(self.current_path, self.session_id)
        view = RegistryView(self.current_path, self.session_id, page=new_page)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=2)
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_path:
            total = len(RegistryEditor.get_subkeys(self.current_path))
            max_page = max(0, (total - 1) // 24)
        else:
            max_page = 0
        new_page = min(max_page, self.page + 1)
        embed = build_registry_embed(self.current_path, self.session_id)
        view = RegistryView(self.current_path, self.session_id, page=new_page)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed = build_registry_embed(self.current_path, self.session_id)
        view = RegistryView(self.current_path, self.session_id, page=self.page)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="New Value", emoji="📝", style=discord.ButtonStyle.primary, row=3)
    async def newvalue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.current_path:
            await interaction.response.send_message("❌ Select a key first!", ephemeral=True)
            return
        await interaction.response.send_modal(NewValueModal(self.current_path, self.session_id, self.page))
    
    @discord.ui.button(label="HKCU Run", emoji="👤", style=discord.ButtonStyle.secondary, row=3)
    async def hkcu_run_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        path = r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run"
        embed = build_registry_embed(path, self.session_id)
        view = RegistryView(path, self.session_id, page=0)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="HKLM Run", emoji="💻", style=discord.ButtonStyle.secondary, row=3)
    async def hklm_run_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        path = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        embed = build_registry_embed(path, self.session_id)
        view = RegistryView(path, self.session_id, page=0)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=4)
    async def back_tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


