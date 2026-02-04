import os
import re
import time
import winreg

current_speed_mbps = 0.0
current_appid = None
current_state = None
log_path = ""
steam_path = ""

def main():
    print("Monitoring steam downloads")
    global log_path, steam_path
    log_path = get_steam_log_path()

    start_time = time.time()
    last_report_time = start_time

    while not os.path.exists(log_path):
        if time.time() - start_time > 300:
            print("No log files detected.")
            return
        time.sleep(1)

    with open(log_path, "r", encoding="utf-8", errors="ignore") as file:
        file.seek(0, os.SEEK_END)

        while True:
            current_time = time.time()
            elapsed = current_time - start_time

            if elapsed > 300:
                print("5 minutes passed, finishing monitoring...")
                report_status()
                break

            while True:
                line = file.readline()
                if not line:
                    break
                parse_line(line.rstrip('\n'))

            if current_time - last_report_time >= 60:
                report_status()
                last_report_time = current_time

            time.sleep(0.1)

def get_steam_log_path() -> str:
    global steam_path
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
            steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
        return os.path.join(steam_path, "logs", "content_log.txt")
    except Exception as e:
        raise RuntimeError(f"Не удалось найти Steam: {e}")

def parse_line(line: str):
    global current_speed_mbps, current_appid, current_state

    if not line.strip():
        return

    line_lower = line.lower()

    appid_match = re.search(r'appid\s+(\d+)', line_lower)
    if appid_match:
        current_appid = appid_match.group(1)

    if "current download rate:" in line_lower:
        speed_match = re.search(r'(\d+(?:\.\d+)?)\s*mbps', line_lower)
        if speed_match:
            current_speed_mbps = float(speed_match.group(1))
        return

    if "state changed" in line_lower and "app update changed" not in line_lower:
        return

    if "app update changed :" in line_lower:
        if "none" in line_lower:
            current_state = "stopped"
        elif "downloading" in line_lower or "staging" in line_lower:
            current_state = "installing"
        elif "running update" in line_lower:
            current_state = "installing"
        else:
            current_state = "unknown"

def get_local_app_name() -> str | None:
    manifest = os.path.join(steam_path, "steamapps", f"appmanifest_{current_appid}.acf")
    if not os.path.exists(manifest):
        print("Not found")
    with open(manifest, "r", encoding="utf-8-sig") as f:
        content = f.read()
        match = re.search(r'"name"\s+"([^"]+)"', content)
        return match.group(1) if match else None
    

def report_status():
    print(f"\n--- Summary [{time.strftime('%H:%M:%S')}] ---")
    if current_appid:
        speed_mbs = current_speed_mbps / 8
        app_name = get_local_app_name()
        print(f"Downloading game: {app_name}")
        print(f"Speed: {current_speed_mbps:.2f} Mbps ({speed_mbs:.2f} MB/s)")
        print(f"Current state: {current_state}")
    else:
        print("No active downloads")
    print("-" * 40)

if __name__ == "__main__":
    main()