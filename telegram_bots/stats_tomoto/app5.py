import time
import csv
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

API_KEY = "1c67a69b2758f598f6edab23ca7dbb7c"

def get_all_tank_names():
    url = "https://api.worldoftanks.eu/wot/encyclopedia/vehicles/"
    params = {"application_id": API_KEY, "language": "en"}
    response = requests.get(url, params=params).json()

    if response["status"] != "ok":
        raise Exception("API failed")

    tanks = response["data"]
    return [tank_info["name"] for tank_info in tanks.values()]

import re

def sanitize_tank_name(name):
    # Remove special characters that break search
    sanitized = re.sub(r"[-/.,'\"!?:]", "", name)
    sanitized = re.sub(r"\s+", " ", sanitized)  # replace multiple spaces with single
    return sanitized.strip()

def get_tomato_stats(driver, wait, tank_name):
    try:
        search_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder='Search 948 tanks...']")
            )
        )
        search_input.click()
        search_input.clear()
        search_input.send_keys(tank_name)

        time.sleep(1)  # let filtering happen

        first_row = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )

        columns = first_row.find_elements(By.TAG_NAME, "td")
        return [col.text.strip() for col in columns]

    except TimeoutException:
        return ["No data"]


if __name__ == "__main__":
    tank_names = get_all_tank_names()
    print(f"Total tanks from WoT API: {len(tank_names)}")

    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 15)

    driver.get("https://tomato.gg/tank-stats/")

    # Close cookie popup if exists
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
        print(f"[{idx}/{len(tank_names)}] Loading stats for: {tank_name}")
        stats = get_tomato_stats(driver, wait, tank_name)
        all_stats.append([tank_name] + stats)

    driver.quit()

    # Save to CSV
    with open("tanks_with_tomato_stats.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Tank Name", "Stat1", "Stat2", "Stat3", "..."])  # adjust headers
        writer.writerows(all_stats)

    print("✔ Saved all stats to tanks_with_tomato_stats.csv")