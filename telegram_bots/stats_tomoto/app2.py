import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

def get_tomato_stats(tank_name):
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

        # ✅ Try to click DISAGREE cookie button if it appears
        try:
            disagree_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.qc-cmp2-close-icon[aria-label='DISAGREE']")
                )
            )
            disagree_button.click()
            print("✔ Cookie popup closed (DISAGREE clicked)")
        except TimeoutException:
            print("ℹ No cookie popup found")

        # ✅ Wait for the search input
        search_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[placeholder='Search 948 tanks...']")
            )
        )

        # Click and type tank name
        search_input.click()
        search_input.clear()
        search_input.send_keys(tank_name)

        # Small delay to let filtering happen
        time.sleep(2)

        # Wait for filtered table row
        first_row = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )

        return first_row.text

    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        driver.quit()

if __name__ == "__main__":
    tank = input("Enter tank name (e.g., EBR 105): ").strip()
    if tank:
        print("--- Scraping Tomato.gg ---")
        result = get_tomato_stats(tank)
        print("\nRaw Data Found:")
        print(result)
    else:
        print("Invalid input.")