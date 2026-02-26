from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
DATA_PATH = HERE / "data.json"
PORTABLE_BASE = (HERE / "profile" / "User Data").resolve()
PORTABLE_BASE.mkdir(parents=True, exist_ok=True)

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    cfg = {
        "login_status": False, 
        "check": False
        }
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg

def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def save_data(data: json):
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def build_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PORTABLE_BASE}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--headless=new")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver