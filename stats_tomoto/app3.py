import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


def get_all_tank_stats():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        target_url = "https://tomato.gg/tank-stats/"
        print(f"Loading: {target_url}")
        driver.get(target_url)

        wait = WebDriverWait(driver, 20)

        # ✅ Close cookie popup if it appears
        try:
            disagree_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.qc-cmp2-close-icon[aria-label='DISAGREE']")
                )
            )
            disagree_button.click()
            print("✔ Cookie popup closed")
        except TimeoutException:
            print("ℹ No cookie popup found")

        # ✅ Wait for table to load
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )

        time.sleep(3)  # extra time for full rendering

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        all_data = []

        print(f"Found {len(rows)} tanks\n")

        for row in rows:
            columns = row.find_elements(By.TAG_NAME, "td")
            row_data = [col.text.strip() for col in columns]
            all_data.append(row_data)

        return all_data

    except Exception as e:
        return f"❌ Error: {str(e)}"

    finally:
        driver.quit()


if __name__ == "__main__":
    print("--- Scraping ALL Tanks from Tomato.gg ---")
    data = get_all_tank_stats()

    if isinstance(data, str):
        print(data)
    else:
        print(f"\nTotal Tanks Scraped: {len(data)}\n")

        # Print first 5 as preview
        for row in data[:5]:
            print(row)

        # Optional: Save to CSV
        with open("tank_stats.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(data)

        print("\n✔ Data saved to tank_stats.csv")