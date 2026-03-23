"""
WhatsApp Web Automation Script (Stable Version)
=============================================

✔ Fixes Chrome crash issue
✔ Uses isolated Chrome profile
✔ Reliable waits
✔ Clean structure

Requirements:
    pip install selenium webdriver-manager

Run:
    python main01.py
"""

import time
import os
import urllib.parse
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
MESSAGE = "Hello! This is an automated message sent via Python"
WAIT_FOR_QR = 60   # Increase if needed


# ─────────────────────────────────────────────
# DRIVER SETUP (FIXED)
# ─────────────────────────────────────────────
def create_driver():
    options = Options()

    # ✅ Create isolated profile (prevents crash)
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")

    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    # Stability flags
    options.add_argument("--remote-debugging-port=9222")

    # Remove automation banner
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(
        ChromeDriverManager().install(),
        log_path="chromedriver.log"
    )

    driver = webdriver.Chrome(service=service, options=options)
    return driver


# ─────────────────────────────────────────────
# WAIT FOR WHATSAPP
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
# OPEN CHAT
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

    time.sleep(2)

    try:
        result = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, f'//span[@title="{recipient}"]')
            )
        )
        result.click()
        print(f"💬 Chat opened: {recipient}")

    except Exception:
        raise Exception(f"❌ Contact '{recipient}' not found.")


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
# MAIN EXECUTION
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
