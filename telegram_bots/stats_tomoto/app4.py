import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


def get_all_tank_stats():
    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    all_data = []

    try:
        driver.get("https://tomato.gg/tank-stats/")
        wait = WebDriverWait(driver, 20)

        # ✅ Close cookie popup
        try:
            disagree_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.qc-cmp2-close-icon[aria-label='DISAGREE']")
                )
            )
            disagree_button.click()
        except TimeoutException:
            pass

        page_number = 1

        while True:
            print(f"Scraping page {page_number}...")

            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
            )

            time.sleep(2)

            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            for row in rows:
                columns = row.find_elements(By.TAG_NAME, "td")
                row_data = [col.text.strip() for col in columns]
                all_data.append(row_data)

            # 🔥 Find the NEXT button (right arrow)
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button.rt-IconButton")

                next_button = buttons[-1]  # last icon button = next arrow

                # If disabled, stop
                if next_button.get_attribute("disabled"):
                    print("No more pages.")
                    break

                driver.execute_script("arguments[0].click();", next_button)

                page_number += 1
                time.sleep(2)

            except Exception:
                print("Pagination ended.")
                break

        return all_data

    finally:
        driver.quit()


if __name__ == "__main__":
    print("Scraping all 948 tanks...")

    data = get_all_tank_stats()

    print(f"\nTotal tanks scraped: {len(data)}")

    with open("all_948_tanks.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(data)

    print("✔ Saved to all_948_tanks.csv")