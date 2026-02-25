import time
import csv
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# ---------------------------
# CONFIG: Put your WoT API key here
# ---------------------------
API_KEY = "1c67a69b2758f598f6edab23ca7dbb7c"  # <-- Put your API key here

# ---------------------------
# Helper: sanitize and rename tank names for Tomato.gg search
# ---------------------------
def sanitize_tank_name(name):
    # Replace PzKpfw → Pz.
    name = name.replace("PzKpfw", "Pz.")
    # Replace Object → Obj
    name = name.replace("Object", "Obj")
    # Remove other special characters
    sanitized = re.sub(r"[-/.,'\"!?:]", "", name)
    # Normalize spaces
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized.strip()

# ---------------------------
# Step 1: Get all tank names from WoT API
# ---------------------------
def get_all_tank_names():
    url = "https://api.worldoftanks.eu/wot/encyclopedia/vehicles/"
    params = {"application_id": API_KEY, "language": "en"}
    response = requests.get(url, params=params).json()
    if response["status"] != "ok":
        raise Exception("API request failed")
    tanks = response["data"]
    return [tank_info["name"] for tank_info in tanks.values()]

# ---------------------------
# Step 2: Get Tomato.gg stats for one tank
# ---------------------------
def get_tomato_stats(driver, wait, tank_name):
    try:
        search_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder^='Search']")
            )
        )
        search_input.click()

        # Clear input via JS for React
        driver.execute_script("""
            arguments[0].value = '';
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        """, search_input)
        time.sleep(0.1)  # allow React to update

        # Send new tank name
        search_input.send_keys(tank_name)
        time.sleep(0.1)

        # Wait max 5 seconds for first row
        try:
            first_row = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
            )
            # Refetch columns immediately to avoid stale element
            columns = first_row.find_elements(By.TAG_NAME, "td")
            return [col.text.strip() for col in columns]
        except (TimeoutException, StaleElementReferenceException):
            return ["No data"]  # skip if not found or stale

    except TimeoutException:
        return ["No data"]
# ---------------------------
# Step 3: Main script
# ---------------------------
if __name__ == "__main__":
    print("Loading all tank names from WoT API...")
    tank_names = get_all_tank_names()
    print(f"Total tanks from WoT API: {len(tank_names)}")

    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)

    print("Opening Tomato.gg...")
    driver.get("https://tomato.gg/tank-stats/")

    # Close cookie popup if present
    try:
        disagree_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.qc-cmp2-close-icon[aria-label='DISAGREE']")
            )
        )
        disagree_button.click()
    except TimeoutException:
        pass

    all_stats = []

    for idx, tank_name in enumerate(tank_names, start=1):
        tank_name_sanitized = sanitize_tank_name(tank_name)
        print(f"[{idx}/{len(tank_names)}] Loading stats for: {tank_name_sanitized}")
        stats = get_tomato_stats(driver, wait, tank_name_sanitized)
        all_stats.append([tank_name] + stats)

    driver.quit()

    # Save to CSV
    if all_stats:
        headers = ["Tank Name"] + [f"Stat{i}" for i in range(1, len(all_stats[0]))]
        with open("tanks_with_tomato_stats.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(all_stats)

        print(f"✔ Saved all stats to tanks_with_tomato_stats.csv ({len(all_stats)} tanks)")
    else:
        print("No data collected.")