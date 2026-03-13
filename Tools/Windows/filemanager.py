import discord
import os
import io
import asyncio
import hashlib
import shutil
import tempfile
from datetime import datetime
from Tools.Windows.manager import WindowsManager


def _get_windows_panel():
    from Tools.Windows.panel import embed_windows_panel, WindowsPanelView
    return embed_windows_panel, WindowsPanelView


def build_file_manager_embed(current_path: str, session_id: str, items: list = None, selected_idx: int = -1, search_query: str = ""):
    """Build the File Manager embed with table layout."""
    if items is None:
        success, path_or_msg, items = WindowsManager.file_manager_list(current_path)
        if not success:
            embed = discord.Embed(
                title=f"📂 File Manager : {session_id}",
                description=f"❌ {path_or_msg}",
                color=discord.Color.red()
            )
            embed.set_footer(text="NwexCord • File Manager")
            return embed, [], 0, 0

    # Filter by search
    if search_query:
        items = [i for i in items if search_query.lower() in i['name'].lower()]

    # Count folders and files
    folder_count = sum(1 for i in items if i['is_dir'])
    file_count = sum(1 for i in items if not i['is_dir'])

    # Build table
    header = f"{'[ Name ]':<32} {'[ Date modified ]':<18} {'[ Type ]':<8} {'[ Size ]'}"
    sep = "━" * 72

    rows = ""
    for i, item in enumerate(items[:25]):
        name = item['name']
        if len(name) > 28:
            name = name[:25] + "..."
        modified = item.get('modified', '')[:16]
        ftype = item.get('type', '')[:6]
        size = item.get('size', '') if not item['is_dir'] else ''

        marker = "►" if i == selected_idx else " "
        icon = "📁" if item['is_dir'] else "📄"
        rows += f"{marker}{icon} {name:<28} {modified:<16} {ftype:<6} {size}\n"

    if not items:
        rows = "  (empty directory)\n"

    table_block = f"```\n{header}\n{sep}\n{rows}```"
    if len(table_block) > 3800:
        table_block = table_block[:3790] + "\n...```"

    selected_name = ""
    if 0 <= selected_idx < len(items):
        selected_name = items[selected_idx]['name']

    embed = discord.Embed(
        title=f"📂 File Manager : {session_id}",
        description=table_block,
        color=discord.Color.from_rgb(0, 120, 215)
    )
    path_display = current_path if len(current_path) <= 60 else "..." + current_path[-57:]
    embed.set_footer(text=f"{path_display}\nFolder[{folder_count}]  Files[{file_count}]")

    return embed, items, folder_count, file_count


class FileManagerItemSelect(discord.ui.Select):
    """Dropdown to select a file/folder from the listing."""
    def __init__(self, session_id: str, current_path: str, items: list):
        self.session_id = session_id
        self.current_path = current_path
        self.items_data = items

        if items:
            options = []
            for i, item in enumerate(items[:25]):
                label = item['name'][:100]
                desc = f"{item['type']} | {item['size']}" if not item['is_dir'] else "Folder"
                emoji = "📁" if item['is_dir'] else "📄"
                options.append(discord.SelectOption(
                    label=label,
                    description=desc[:100],
                    value=str(i),
                    emoji=emoji
                ))
        else:
            options = [discord.SelectOption(label="(empty)", value="_none")]

        super().__init__(placeholder="📂 Select a file or folder...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "_none":
            await interaction.response.defer()
            return

        idx = int(selected)
        # If it's a directory, navigate into it
        if idx < len(self.items_data) and self.items_data[idx]['is_dir']:
            new_path = os.path.join(self.current_path, self.items_data[idx]['name'])
            embed, items, fc, fic = build_file_manager_embed(new_path, self.session_id)
            view = FileManagerView(self.session_id, new_path, items)
            await interaction.response.edit_message(content=None, embed=embed, view=view)
        else:
            # Select the file and show actions
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id, self.items_data, selected_idx=idx)
            view = FileManagerView(self.session_id, self.current_path, self.items_data, selected_idx=idx)
            await interaction.response.edit_message(content=None, embed=embed, view=view)


class FileManagerActionSelect(discord.ui.Select):
    """Dropdown for file/folder actions."""
    def __init__(self, session_id: str, current_path: str, items: list, selected_idx: int = -1):
        self.session_id = session_id
        self.current_path = current_path
        self.items_data = items
        self.selected_idx = selected_idx

        options = [
            discord.SelectOption(label="Back", emoji="⬅", value="back", description="Go to parent directory"),
            discord.SelectOption(label="Refresh", emoji="🔄", value="refresh", description="Refresh file listing"),
            discord.SelectOption(label="Execute", emoji="▶️", value="execute", description="Execute selected (Normal)"),
            discord.SelectOption(label="Execute Hidden", emoji="👻", value="execute_hidden", description="Execute hidden"),
            discord.SelectOption(label="Execute RunAs", emoji="🛡️", value="execute_runas", description="Execute as admin"),
            discord.SelectOption(label="Delete", emoji="🗑️", value="delete", description="Delete selected item"),
            discord.SelectOption(label="Download", emoji="⬇", value="download", description="Download selected file"),
            discord.SelectOption(label="Rename", emoji="✏️", value="rename", description="Rename selected item"),
            discord.SelectOption(label="Upload", emoji="⬆", value="upload", description="Upload a file here"),
            discord.SelectOption(label="New Folder", emoji="📁", value="new_folder", description="Create new folder"),
            discord.SelectOption(label="New File", emoji="📄", value="new_file", description="Create new file"),
            discord.SelectOption(label="Edit", emoji="📝", value="edit", description="Edit text file"),
            discord.SelectOption(label="Lock Folder", emoji="🔒", value="lock", description="Lock selected folder"),
            discord.SelectOption(label="Unlock Folder", emoji="🔓", value="unlock", description="Unlock selected folder"),
            discord.SelectOption(label="Show File/Folder", emoji="👁", value="show", description="Unhide file/folder"),
            discord.SelectOption(label="Hide File/Folder", emoji="🙈", value="hide", description="Hide file/folder"),
            discord.SelectOption(label="Set Background", emoji="🖼️", value="set_bg", description="Set image as wallpaper"),
            discord.SelectOption(label="Download Folder", emoji="📦", value="download_folder", description="Download folder as zip"),
        ]

        super().__init__(placeholder="⚡ Select an action...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        action = self.values[0]
        selected_item = self.items_data[self.selected_idx] if 0 <= self.selected_idx < len(self.items_data) else None
        selected_path = selected_item['full_path'] if selected_item else None

        if action == "back":
            parent = os.path.dirname(self.current_path)
            if not parent or parent == self.current_path:
                parent = self.current_path
            embed, items, fc, fic = build_file_manager_embed(parent, self.session_id)
            view = FileManagerView(self.session_id, parent, items)
            await interaction.response.edit_message(content=None, embed=embed, view=view)

        elif action == "refresh":
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.response.edit_message(content=None, embed=embed, view=view)

        elif action in ("execute", "execute_hidden", "execute_runas"):
            if not selected_path:
                await interaction.response.send_message("❌ Select a file first!", ephemeral=True)
                return
            mode_map = {"execute": "normal", "execute_hidden": "hidden", "execute_runas": "runas"}
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.file_execute, selected_path, mode_map[action])
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "✅" if success else "❌"
            embed.add_field(name=f"{status} Execute", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "delete":
            if not selected_path:
                await interaction.response.send_message("❌ Select an item first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.file_delete, selected_path)
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "✅" if success else "❌"
            embed.add_field(name=f"{status} Delete", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "download":
            if not selected_path or not os.path.isfile(selected_path):
                await interaction.response.send_message("❌ Select a file first!", ephemeral=True)
                return
            try:
                file_size = os.path.getsize(selected_path)
                if file_size > 25 * 1024 * 1024:  # 25MB Discord limit
                    await interaction.response.send_message("❌ File too large (>25MB).", ephemeral=True)
                    return
                await interaction.response.defer()
                file = discord.File(selected_path, filename=os.path.basename(selected_path))
                await interaction.followup.send(file=file, ephemeral=False)
            except Exception as e:
                try:
                    await interaction.response.send_message(f"❌ {e}", ephemeral=True)
                except:
                    await interaction.followup.send(f"❌ {e}", ephemeral=True)

        elif action == "rename":
            if not selected_path:
                await interaction.response.send_message("❌ Select an item first!", ephemeral=True)
                return
            await interaction.response.send_modal(FMRenameModal(self.session_id, self.current_path, selected_path))

        elif action == "upload":
            await interaction.response.send_message(
                "📤 **Upload a file** by sending it as an attachment in this channel.\n"
                f"It will be saved to: `{self.current_path}`\n\n"
                "*Reply to this message with an attached file.*",
                ephemeral=True
            )

        elif action == "new_folder":
            await interaction.response.send_modal(FMNewFolderModal(self.session_id, self.current_path))

        elif action == "new_file":
            await interaction.response.send_modal(FMNewFileModal(self.session_id, self.current_path))

        elif action == "edit":
            if not selected_path or not os.path.isfile(selected_path):
                await interaction.response.send_message("❌ Select a text file first!", ephemeral=True)
                return
            success, content = WindowsManager.file_edit_read(selected_path)
            if not success:
                await interaction.response.send_message(f"❌ {content}", ephemeral=True)
                return
            await interaction.response.send_modal(FMEditFileModal(self.session_id, self.current_path, selected_path, content))

        elif action == "lock":
            if not selected_path or not os.path.isdir(selected_path):
                await interaction.response.send_message("❌ Select a folder first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.folder_lock, selected_path)
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "🔒" if success else "❌"
            embed.add_field(name=f"{status} Folder Lock", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "unlock":
            if not selected_path or not os.path.isdir(selected_path):
                await interaction.response.send_message("❌ Select a folder first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.folder_unlock, selected_path)
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "🔓" if success else "❌"
            embed.add_field(name=f"{status} Folder Unlock", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "show":
            if not selected_path:
                await interaction.response.send_message("❌ Select an item first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.file_show, selected_path)
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "👁" if success else "❌"
            embed.add_field(name=f"{status} Show", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "hide":
            if not selected_path:
                await interaction.response.send_message("❌ Select an item first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.file_hide, selected_path)
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "🙈" if success else "❌"
            embed.add_field(name=f"{status} Hide", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "set_bg":
            if not selected_path or not os.path.isfile(selected_path):
                await interaction.response.send_message("❌ Select an image file first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, msg = await loop.run_in_executor(None, WindowsManager.file_set_background, selected_path)
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
            status = "🖼️" if success else "❌"
            embed.add_field(name=f"{status} Set Background", value=msg, inline=False)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)

        elif action == "download_folder":
            if not selected_path or not os.path.isdir(selected_path):
                await interaction.response.send_message("❌ Select a folder first!", ephemeral=True)
                return
            await interaction.response.defer()
            loop = asyncio.get_event_loop()
            success, result = await loop.run_in_executor(None, WindowsManager.folder_download_zip, selected_path)
            if success:
                try:
                    file_size = os.path.getsize(result)
                    if file_size > 25 * 1024 * 1024:
                        await interaction.followup.send("❌ Zip file too large (>25MB).", ephemeral=True)
                        os.remove(result)
                        return
                    file = discord.File(result, filename=os.path.basename(result))
                    await interaction.followup.send(file=file, ephemeral=False)
                    os.remove(result)
                except Exception as e:
                    await interaction.followup.send(f"❌ {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {result}", ephemeral=True)


class FMRenameModal(discord.ui.Modal, title="✏️ Rename"):
    new_name = discord.ui.TextInput(label="New Name", placeholder="new_name.txt", required=True)

    def __init__(self, session_id: str, current_path: str, target_path: str):
        super().__init__()
        self.session_id = session_id
        self.current_path = current_path
        self.target_path = target_path
        self.new_name.default = os.path.basename(target_path)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.file_rename, self.target_path, str(self.new_name))
        embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
        status = "✅" if success else "❌"
        embed.add_field(name=f"{status} Rename", value=msg, inline=False)
        view = FileManagerView(self.session_id, self.current_path, items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)


class FMNewFolderModal(discord.ui.Modal, title="📁 New Folder"):
    folder_name = discord.ui.TextInput(label="Folder Name", placeholder="New Folder", required=True)

    def __init__(self, session_id: str, current_path: str):
        super().__init__()
        self.session_id = session_id
        self.current_path = current_path

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.file_new_folder, self.current_path, str(self.folder_name))
        embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
        status = "✅" if success else "❌"
        embed.add_field(name=f"{status} New Folder", value=msg, inline=False)
        view = FileManagerView(self.session_id, self.current_path, items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)


class FMNewFileModal(discord.ui.Modal, title="📄 New File"):
    file_name = discord.ui.TextInput(label="File Name", placeholder="file.txt", required=True)
    file_content = discord.ui.TextInput(label="Content (optional)", placeholder="File content...", style=discord.TextStyle.paragraph, required=False)

    def __init__(self, session_id: str, current_path: str):
        super().__init__()
        self.session_id = session_id
        self.current_path = current_path

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        content = str(self.file_content) if self.file_content else ""
        success, msg = await loop.run_in_executor(None, WindowsManager.file_new_file, self.current_path, str(self.file_name), content)
        embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
        status = "✅" if success else "❌"
        embed.add_field(name=f"{status} New File", value=msg, inline=False)
        view = FileManagerView(self.session_id, self.current_path, items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)


class FMEditFileModal(discord.ui.Modal, title="📝 Edit File"):
    file_content = discord.ui.TextInput(label="File Content", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, session_id: str, current_path: str, target_path: str, content: str):
        super().__init__()
        self.session_id = session_id
        self.current_path = current_path
        self.target_path = target_path
        self.file_content.default = content[:4000]

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_event_loop()
        success, msg = await loop.run_in_executor(None, WindowsManager.file_edit_write, self.target_path, str(self.file_content))
        embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
        status = "✅" if success else "❌"
        embed.add_field(name=f"{status} Edit", value=msg, inline=False)
        view = FileManagerView(self.session_id, self.current_path, items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)


class FMSearchModal(discord.ui.Modal, title="🔍 Search Files"):
    search_query = discord.ui.TextInput(label="Search", placeholder="*.txt, filename...", required=True)

    def __init__(self, session_id: str, current_path: str):
        super().__init__()
        self.session_id = session_id
        self.current_path = current_path

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        success, path_or_msg, all_items = WindowsManager.file_manager_list(self.current_path)
        query = str(self.search_query).strip()
        if success:
            embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id, all_items, search_query=query)
            view = FileManagerView(self.session_id, self.current_path, items)
            await interaction.edit_original_response(content=None, embed=embed, view=view)
        else:
            embed = discord.Embed(title="❌ Search Error", description=path_or_msg, color=discord.Color.red())
            await interaction.edit_original_response(content=None, embed=embed, view=FileManagerView(self.session_id, self.current_path, []))


class FileManagerView(discord.ui.View):
    """Full interactive File Manager view."""
    def __init__(self, session_id: str, current_path: str, items: list = None, selected_idx: int = -1):
        super().__init__(timeout=300)
        self.session_id = session_id
        self.current_path = current_path
        self.selected_idx = selected_idx

        if items is None:
            success, path_or_msg, items = WindowsManager.file_manager_list(current_path)
            if not success:
                items = []
        self.items_data = items

        # Row 0: File/folder select
        self.add_item(FileManagerItemSelect(session_id, current_path, items))
        # Row 1: Action select
        self.add_item(FileManagerActionSelect(session_id, current_path, items, selected_idx))

    @discord.ui.button(label="⬅ Back", style=discord.ButtonStyle.secondary, row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        parent = os.path.dirname(self.current_path)
        if not parent or parent == self.current_path:
            parent = self.current_path
        embed, items, fc, fic = build_file_manager_embed(parent, self.session_id)
        view = FileManagerView(self.session_id, parent, items)
        await interaction.response.edit_message(content=None, embed=embed, view=view)

    @discord.ui.button(label="Refresh", emoji="🔄", style=discord.ButtonStyle.secondary, row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        embed, items, fc, fic = build_file_manager_embed(self.current_path, self.session_id)
        view = FileManagerView(self.session_id, self.current_path, items)
        await interaction.edit_original_response(content=None, embed=embed, view=view)

    @discord.ui.button(label="Search", emoji="🔍", style=discord.ButtonStyle.secondary, row=2)
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FMSearchModal(self.session_id, self.current_path))

    @discord.ui.button(label="Back to Windows", emoji="🪟", style=discord.ButtonStyle.secondary, row=2)
    async def back_windows_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=_get_windows_panel()[0](), view=_get_windows_panel()[1]())


