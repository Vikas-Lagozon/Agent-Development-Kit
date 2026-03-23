"""
WhatsApp Web Automation Script (Background Stable Version)
=========================================================

✔ Runs in background (no visible UI)
✔ Logs stored in logs/ folder
✔ Persistent session
✔ Smart fuzzy matching (80%+)
✔ More stable than headless

Requirements:
    pip install selenium webdriver-manager rapidfuzz
"""

import time
import os
import logging
import urllib.parse
from datetime import date
from rapidfuzz import fuzz

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ─────────────────────────────────────────────
# LOGGER SETUP
# ─────────────────────────────────────────────
FILENAME = os.path.splitext(os.path.basename(__file__))[0]

LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    LOG_DIR,
    f"log_{FILENAME}_{date.today()}.log"
)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
RECIPIENT = "Yash Bansal"
MESSAGE = "Hello! This is an automated message sent via Python"
WAIT_FOR_QR = 60


# ─────────────────────────────────────────────
# DRIVER SETUP (BACKGROUND MODE)
# ─────────────────────────────────────────────
def create_driver():
    options = Options()

    # ❌ DO NOT use headless (unstable for WhatsApp)
    # options.add_argument("--headless=new")

    # ✅ Persistent profile
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")

    # ✅ Run in background (hidden window)
    options.add_argument("--window-position=-32000,-32000")
    options.add_argument("--window-size=1920,1080")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(
        ChromeDriverManager().install(),
        log_path="chromedriver.log"
    )

    driver = webdriver.Chrome(service=service, options=options)

    # ✅ Minimize window (extra safety)
    driver.minimize_window()

    return driver


# ─────────────────────────────────────────────
# WAIT FOR WHATSAPP LOAD
# ─────────────────────────────────────────────
def wait_for_whatsapp_load(driver, timeout):
    logger.info(f"Waiting up to {timeout}s for WhatsApp Web...")

    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        )
    )

    logger.info("WhatsApp Web loaded successfully.")


# ─────────────────────────────────────────────
# SMART OPEN CHAT
# ─────────────────────────────────────────────
def open_chat(driver, recipient):
    logger.info(f"Searching for '{recipient}'...")

    search_box = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        )
    )

    search_box.click()
    time.sleep(1)
    search_box.clear()
    search_box.send_keys(recipient)

    time.sleep(3)

    results = driver.find_elements(By.XPATH, '//span[@dir="auto"]')

    best_match = None
    best_score = 0

    for r in results:
        name = r.text.strip()
        if not name:
            continue

        score = fuzz.partial_ratio(recipient.lower(), name.lower())
        logger.info(f"Checking: {name} → Score: {score}")

        if score > best_score:
            best_score = score
            best_match = r

    if best_match and best_score >= 80:
        logger.info(f"Best match: {best_match.text} ({best_score}%)")
        best_match.click()
        logger.info(f"Chat opened: {best_match.text}")
    else:
        raise Exception(f"No close match found for '{recipient}'")


# ─────────────────────────────────────────────
# SEND MESSAGE
# ─────────────────────────────────────────────
def send_message(driver, message):
    logger.info("Typing message...")

    msg_box = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
        )
    )

    msg_box.click()
    time.sleep(0.5)

    for line in message.split("\n"):
        msg_box.send_keys(line)
        msg_box.send_keys(Keys.SHIFT + Keys.ENTER)

    time.sleep(1)
    msg_box.send_keys(Keys.ENTER)

    logger.info("Message sent successfully!")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    driver = None

    try:
        logger.info("Starting WhatsApp automation...")

        driver = create_driver()
        driver.get("https://web.whatsapp.com")

        wait_for_whatsapp_load(driver, WAIT_FOR_QR)
        open_chat(driver, RECIPIENT)
        send_message(driver, MESSAGE)

        time.sleep(3)

        logger.info("Process completed successfully.")

    except Exception as e:
        logger.error(f"Error occurred: {e}")

    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
