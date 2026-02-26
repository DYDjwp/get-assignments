from pathlib import Path
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config_tool import save_config


HERE = Path(__file__).resolve().parent
PORTABLE_BASE = (HERE / "profile" / "User Data").resolve()
PORTABLE_BASE.mkdir(parents=True, exist_ok=True)

TIMEOUT_SHORT = 10
TIMEOUT_LONG = 60


def build_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PORTABLE_BASE}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def wait_any(wait: WebDriverWait, *conditions):
    """Waiting for any condition to succeed (Selenium4's EC.any_of sometimes has version inconsistencies, so a custom one is written here)."""
    end = time.time() + wait._timeout
    last_err = None
    while time.time() < end:
        for cond in conditions:
            try:
                res = cond(wait._driver)
                if res:
                    return res
            except Exception as e:
                last_err = e
        time.sleep(0.1)
    raise TimeoutException(f"Timed out waiting for any condition. last_err={last_err!r}")


def safe_click(driver: webdriver.Chrome, locator, timeout=TIMEOUT_SHORT, retries=3):
    wait = WebDriverWait(driver, timeout)
    for i in range(retries):
        try:
            el = wait.until(EC.element_to_be_clickable(locator))
            el.click()
            return
        except (StaleElementReferenceException, ElementClickInterceptedException):
            if i == retries - 1:
                raise
            time.sleep(0.2)


def safe_type(driver: webdriver.Chrome, locator, text: str, timeout=TIMEOUT_SHORT, clear_first=True, retries=3):
    wait = WebDriverWait(driver, timeout)
    for i in range(retries):
        try:
            el = wait.until(EC.visibility_of_element_located(locator))
            if clear_first:
                el.clear()
            el.send_keys(text)
            return
        except StaleElementReferenceException:
            if i == retries - 1:
                raise
            time.sleep(0.2)


def google_login(cfg):
    driver = build_driver()
    try:
        driver.get("https://accounts.google.com/")

        wait = WebDriverWait(driver, TIMEOUT_SHORT)

        try:
            email_box = wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
            need_login = True
        except TimeoutException:
            need_login = False

        if not need_login:
            print("already logged in or something wrong")
            return
        try:
            email = cfg["email"]
        except:
            driver.quit()
            raise KeyError("Missing required config key: 'email'")

        safe_type(driver, (By.ID, "identifierId"), email, timeout=TIMEOUT_SHORT)
        safe_click(driver, (By.ID, "identifierNext"), timeout=TIMEOUT_SHORT)

        wait2 = WebDriverWait(driver, TIMEOUT_LONG)
        result = wait_any(
            wait2,
            EC.visibility_of_element_located((By.XPATH, "//input[@type='password']")),
            EC.presence_of_element_located((By.XPATH, "//*[contains(@data-challengetype,'')]")),  
            EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Try another way') or contains(., '验证') or contains(., 'Verify')]")),
        )

        try:
            driver.find_element(By.XPATH, "//input[@type='password']")
            try:
                password = cfg["password"]
            except:
                driver.quit()
                raise KeyError("can't find password on config")

            safe_type(driver, (By.XPATH, "//input[@type='password']"), password, timeout=TIMEOUT_LONG, clear_first=False)
            safe_click(driver, (By.ID, "passwordNext"), timeout=TIMEOUT_SHORT)
            time.sleep(1)
            if driver.find_elements(By.XPATH, "//span[contains(text(), 'Wrong password')]"):
                cfg["login_status"] = False
                cfg["check"] = False
                save_config(cfg)
                driver.quit()
                raise RuntimeError("Wrong password entered")
            print("Email/password submitted")
        except Exception:
            driver.quit()
            raise RuntimeError("It appears that the password input page was not accessed, which may have triggered a two-factor authentication/abnormal process.")

    except WebDriverException as e:
        raise RuntimeError(f"Browser driver error: {e}")
    except Exception as e:
        raise RuntimeError(f"An unknown error occurred: {e}")
    finally:
        try:
            driver.quit()
        except Exception as e:
            raise RuntimeError(f"An unknown error occurred: {e}")
