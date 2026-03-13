import discord
import subprocess
import asyncio


def _get_tools_panel():
    from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
    return embed_tools_panel, ToolsPanelView


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
        await interaction.response.defer()
        new_conns = TCPConnectionsManager.get_connections()
        embed, conns, pg, tp = build_tcp_embed(self.session_id, 0, new_conns)
        view = TCPConnectionsView(self.session_id, 0, new_conns)
        await interaction.edit_original_response(content=None, embed=embed, view=view)
        
    @discord.ui.button(label="Close", emoji="\u274c", style=discord.ButtonStyle.danger, row=1)
    async def close_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_idx < 0 or self.selected_idx >= len(self.connections):
            await interaction.response.send_message("\u274c Please select a connection first!", ephemeral=True)
            return
            
        await interaction.response.defer()
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
        await interaction.edit_original_response(content=None, embed=embed, view=view)
    
    @discord.ui.button(label="Back to Tools", emoji="\u2b05", style=discord.ButtonStyle.secondary, row=1)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())


