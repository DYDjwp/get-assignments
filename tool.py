from __future__ import annotations
from pathlib import Path
import sys, itertools, time, threading, getpass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from google_login import google_login
from config_tool import load_config, save_config

HERE = Path(__file__).resolve().parent
PORTABLE_BASE = (HERE / "profile" / "User Data").resolve()
PORTABLE_BASE.mkdir(parents=True, exist_ok=True)

class LiveProgress:
    def __init__(self, width=20, text="loading get apikey", stream=sys.stderr):
        self.width = width
        self.text = text
        self.stream = stream
        self._percent = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def update(self, percent: int):
        self._percent = max(0, min(100, int(percent)))

    def _run(self):
        spinner = itertools.cycle("|/-\\")
        while not self._stop.is_set():
            ch = next(spinner)
            filled = self._percent * self.width // 100
            bar = "█" * filled + " " * (self.width - filled)
            self.stream.write(f"\r[{bar}] {self._percent:3d}% {self.text}{ch}")
            self.stream.flush()
            time.sleep(0.06)

    def done(self, ok=True):
        self._stop.set()
        self._thread.join()
        bar = "█" * self.width
        mark = "✓" if ok else "✗"
        self.stream.write(f"\r[{bar}] 100% {self.text} {mark}\n")
        self.stream.flush()

MYSCHOOLAPP_LOGIN_URL = (
    "https://app.blackbaud.com/signin/?svcid=edu&envid=p-d7NVWib9D0e6P7mLFSA-kw"
    "&redirecturl=https:%2F%2Fhillbrook.myschoolapp.com%2Fapp%3Fbb_id%3D1%26svcid%3Dedu%26envid%3Dp-d7NVWib9D0e6P7mLFSA-kw%23login"
)

LOCATORS = [
    (By.XPATH, "//button[contains(normalize-space(.), 'Continue with Google')]"),
    (By.XPATH, "//*[contains(@data-sky-icon,'google-branded')]/ancestor::button[1]"),
    (By.XPATH, "//button[.//*[contains(normalize-space(text()), 'Continue with Google')]]"),
    (By.XPATH, "//button[contains(@class,'sky-btn') and contains(normalize-space(.), 'Continue with Google')]"),
]

def build_chrome_options(headless: bool = False) -> webdriver.ChromeOptions:
    opts = webdriver.ChromeOptions()
    opts.add_argument(f"--user-data-dir={PORTABLE_BASE}")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1400,900")
    else:
        opts.add_argument("--start-maximized")
    return opts

def create_driver(headless: bool = False) -> webdriver.Chrome:
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=build_chrome_options(headless=headless))

def wait_until_all_windows_closed(driver: webdriver.Chrome, poll_sec: float = 0.5):
    while True:
        try:
            _ = driver.window_handles  # WebDriverException
            time.sleep(poll_sec)
        except WebDriverException:
            break

def google(cfg):
    try:
        google_login(cfg)
        cfg["login_status"] = True
        cfg["check"] = True
        save_config(cfg)
        return True
    except Exception as e:
        print(e)
        cfg["login_status"] = False
        cfg["check"] = False
        save_config(cfg)
        return False

def do_myschoolapp_google_continue(headless: bool = False):
    lp = LiveProgress(text="loading...")
    lp.start()
    lp.update(0)
    driver = create_driver(headless=headless)
    driver.get(MYSCHOOLAPP_LOGIN_URL)
    wait = WebDriverWait(driver, 30)

    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except Exception:
        pass

    def _scroll_and_click(elem):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
        except Exception:
            pass
        try:
            elem.click()
        except Exception:
            driver.execute_script("arguments[0].click();", elem)

    def _try_locators_in_context():
        for by, sel in LOCATORS:
            try:
                el = wait.until(EC.element_to_be_clickable((by, sel)))
                if el:
                    _scroll_and_click(el)
                    return True
            except Exception:
                continue
        return False

    if not _try_locators_in_context():
        tried_frames = set()

        def _search_frames(depth=0, max_depth=2):
            if depth > max_depth:
                return False
            frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
            for fr in frames:
                fid = getattr(fr, "id", id(fr))
                if fid in tried_frames:
                    continue
                tried_frames.add(fid)
                try:
                    driver.switch_to.frame(fr)
                    if _try_locators_in_context():
                        driver.switch_to.default_content()
                        return True
                    if _search_frames(depth + 1, max_depth):
                        driver.switch_to.default_content()
                        return True
                except Exception:
                    pass
                finally:
                    driver.switch_to.default_content()
            return False

        if not _search_frames():
            def _js_try_ctx():
                js = """
                const btn = Array.from(document.querySelectorAll('button'))
                  .find(b => (b.innerText||'').toLowerCase().includes('continue with google'));
                return btn || null;
                """
                try:
                    el = driver.execute_script(js)
                    if el:
                        try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        except Exception: pass
                        try: driver.execute_script("arguments[0].click();", el)
                        except Exception: pass
                        return True
                except Exception:
                    pass
                return False

            if not _js_try_ctx():
                frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
                for fr in frames:
                    try:
                        driver.switch_to.frame(fr)
                        if _js_try_ctx():
                            driver.switch_to.default_content()
                            break
                    finally:
                        driver.switch_to.default_content()
                else:
                    driver.quit()
                    raise TimeoutException("The Continue with Google button could not be found or clicked: This may be due to changes in the page structure/iframe.")
    lp.update(30)
    for i in range(8):
        time.sleep(1)
        lp.update(35 + i * 5)
    t_val = None
    try:
        c = driver.get_cookie("t")
        if c and "value" in c:
            t_val = c["value"]
    except Exception:
        pass

    if t_val is None:
        try:
            for c in driver.get_cookies():
                if c.get("name") == "t":
                    t_val = c.get("value")
                    break
        except Exception:
            pass
    lp.update(100)
    lp.done(ok=True)
    print("t=", t_val if t_val is not None else "")
    driver.quit()
    return t_val

def get_token():
    t = None
    cfg = load_config()
    if not cfg.get("check"):
        cfg["email"] = input("please input your email address:")
        cfg["password"] = getpass.getpass("please input your password:")
    if not cfg.get("login_status"):
        if google(cfg):
            print("login completed")
            t = do_myschoolapp_google_continue(headless=True)
            cfg["t"] = t
            save_config(cfg)
        else:
            print("login error")
    else:
        t = do_myschoolapp_google_continue(headless=True)
        cfg["t"] = t
        save_config(cfg)
    return t 