import requests
from config_tool import load_config, save_config, save_data
from tool import get_token

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://hillbrook.myschoolapp.com",
    "Referer": "https://hillbrook.myschoolapp.com/",
    "X-Requested-With": "XMLHttpRequest",
}

def request_apikey():
    return get_token()
    
def analyze(data, cfg):
    items = []
    for section in ("DueToday", "DueTomorrow", "DueThisWeek", "DueNextWeek", "DueAfterNextWeek"):
        for a in data.get(section, []):
            items.append({
                "course": a.get("GroupName"),
                "title": a.get("ShortDescription"),
                "due": a.get("DateDue"),
                "assigned": a.get("DateAssigned"),
        })
    if not items:
        print("please check the login status and relogin")
        cfg["login_status"] = False 
        cfg["check"] = False
        save_config(cfg)
    else:
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
        break
    analyze(res, cfg)
    save_data(res)

if __name__ == "__main__":
    main()
