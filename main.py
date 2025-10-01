import subprocess, sys
import requests
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
DATA_PATH = HERE / "data.json"

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg = {"first_run": False}
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg

headers = {
    # 基本常用头
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://hillbrook.myschoolapp.com",
    "Referer": "https://hillbrook.myschoolapp.com/",
    "X-Requested-With": "XMLHttpRequest",
}

cmd = [sys.executable, "tool.py", "arg1", "arg2"]

def request_apikey():
    res = subprocess.run(
        cmd, 
        text=True,             
        encoding="utf-8",      
        check=False, 
        stdout=subprocess.PIPE,
        stderr=None,          
        timeout=3000            
    )
    print()
    print("Exit code:", res.returncode)
    m = re.search(r't=\s*([0-9a-fA-F-]+)', res.stdout)
    if m:
        t = m.group(1)
        return t or None
    else:
        return None
    
def analyze(data):
    items = []
    for section in ("DueToday", "DueTomorrow", "DueThisWeek", "DueNextWeek", "DueAfterNextWeek"):
        for a in data.get(section, []):
            items.append({
                "course": a.get("GroupName"),
                "title": a.get("ShortDescription"),
                "due": a.get("DateDue"),
                "assigned": a.get("DateAssigned"),
        })
    for it in items:
        print(it["course"], "|", it["title"], "|", it["due"], "|", it["assigned"])


def main():
    time = 3
    cfg = load_config()
    if not cfg.get("t"):
        print("can not find apikey in config")
        t = request_apikey()
    else:
        t = cfg.get("t")
    while time > 0:
        url = f"https://hillbrook.myschoolapp.com/api/assignment2/StudentAssignmentCenterGet?displayByDueDate=true&t={t}"
        response = requests.get(url, headers=headers)
        res = response.json()
        try:
            if res['Error']:
                print("apikey has expired or is incorrect.")
                t = request_apikey()
                time -= 1
                continue
        except Exception:
            pass    
        analyze(res)
        break

if __name__ == "__main__":
    main()
