import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_all_tanks():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Adding a window size helps headless browsers "see" the table better
    options.add_argument("--window-size=1920,1080") 

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    data = []

    try:
        driver.get("https://poliroid.me/gunmarks/?server=EU")
        wait = WebDriverWait(driver, 20)

        # 1. Wait for the table row to actually have text (ensures JS finished loading data)
        wait.until(lambda d: d.find_element(By.CSS_SELECTOR, "table tbody tr td").text.strip() != "")

        # 2. Use textContent to grab data even if the browser thinks it's "hidden"
        headers = [th.get_attribute("textContent").strip() for th in driver.find_elements(By.CSS_SELECTOR, "table thead tr th")]
        
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            
            if len(cols) < 2:
                continue
            
            # Using textContent here as well for reliability
            row_data = [c.get_attribute("textContent").strip() for c in cols]

            # Map headers to column data safely
            tank_info = {headers[i]: row_data[i] for i in range(min(len(headers), len(row_data)))}
            
            if tank_info:
                data.append(tank_info)

        return data

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    all_data = scrape_all_tanks()

    if all_data:
        with open("tanks_data.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Successfully saved {len(all_data)} tanks to tanks_data.json")