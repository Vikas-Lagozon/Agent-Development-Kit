"""
WhatsApp Web Automation Script (Smart Matching Version)
======================================================

✔ Stable Chrome launch (no crash)
✔ Persistent login (no repeated QR scan)
✔ Fuzzy name matching (80% similarity)
✔ Clean & reliable execution

Requirements:
    pip install selenium webdriver-manager rapidfuzz
"""

import time
import os
import urllib.parse
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
# CONFIG
# ─────────────────────────────────────────────
RECIPIENT = "Yash Bansal"  
MESSAGE = "Kitne baje aaya tha aaj?"
WAIT_FOR_QR = 60   # seconds


# ─────────────────────────────────────────────
# DRIVER SETUP
# ─────────────────────────────────────────────
def create_driver():
    options = Options()

    # ✅ Isolated profile (prevents crash)
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")

    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(
        ChromeDriverManager().install(),
        log_path="chromedriver.log"
    )

    driver = webdriver.Chrome(service=service, options=options)
    return driver


# ─────────────────────────────────────────────
# WAIT FOR WHATSAPP LOAD
# ─────────────────────────────────────────────
def wait_for_whatsapp_load(driver, timeout):
    print(f"⏳ Waiting up to {timeout}s for WhatsApp Web...")

    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        )
    )

    print("✅ WhatsApp Web loaded successfully.")


# ─────────────────────────────────────────────
# SMART OPEN CHAT (FUZZY MATCHING)
# ─────────────────────────────────────────────
def open_chat(driver, recipient):
    print(f"🔍 Searching for '{recipient}'...")

    search_box = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        )
    )

    search_box.click()
    time.sleep(1)
    search_box.clear()
    search_box.send_keys(recipient)

    time.sleep(3)  # allow results to load

    # Get all visible chat names
    results = driver.find_elements(By.XPATH, '//span[@dir="auto"]')

    best_match = None
    best_score = 0

    for r in results:
        name = r.text.strip()

        if not name:
            continue

        score = fuzz.partial_ratio(recipient.lower(), name.lower())
        print(f"🔎 Checking: {name} → Score: {score}")

        if score > best_score:
            best_score = score
            best_match = r

    # Threshold check
    if best_match and best_score >= 80:
        print(f"✅ Best match: {best_match.text} ({best_score}%)")
        best_match.click()
        print(f"💬 Chat opened: {best_match.text}")
    else:
        raise Exception(f"❌ No close match found for '{recipient}'")


# ─────────────────────────────────────────────
# SEND MESSAGE
# ─────────────────────────────────────────────
def send_message(driver, message):
    print("✍️ Typing message...")

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

    print("🚀 Message sent successfully!")


# ─────────────────────────────────────────────
# OPTIONAL: SEND VIA PHONE NUMBER
# ─────────────────────────────────────────────
def send_via_url(phone, message):
    encoded = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"

    driver = create_driver()
    driver.get(url)

    print(f"⏳ Waiting {WAIT_FOR_QR}s for QR scan...")
    time.sleep(WAIT_FOR_QR)

    try:
        send_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[@aria-label="Send"]')
            )
        )
        send_btn.click()
        print("🚀 Message sent via phone number!")

    except Exception as e:
        print(f"❌ Failed to send: {e}")

    finally:
        time.sleep(3)
        driver.quit()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    driver = None

    try:
        driver = create_driver()
        driver.get("https://web.whatsapp.com")

        wait_for_whatsapp_load(driver, WAIT_FOR_QR)
        open_chat(driver, RECIPIENT)
        send_message(driver, MESSAGE)

        time.sleep(5)

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        if driver:
            driver.quit()
            print("🛑 Browser closed.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()
