import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def scrape_tank_data(driver, url):
    """Scrapes a specific URL and returns the data as a list."""
    driver.get(url)
    time.sleep(5)  # Wait for table to load
    
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    data = []

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 6:
            tank_name = cols[3].text
            values = [col.text for col in cols[4:]]
            data.append({"tank": tank_name, "values": values})
            
    return data

def run_combined_scraper():
    options = Options()
    # options.add_argument("--headless")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    combined_data = {}

    try:
        # Scrape Mastery
        print("Scraping Mastery data...")
        combined_data["mastery"] = scrape_tank_data(driver, "https://poliroid.me/mastery//?server=EU")
        
        # Scrape Gunmarks
        print("Scraping Gunmarks data...")
        combined_data["gunmarks"] = scrape_tank_data(driver, "https://poliroid.me/gunmarks/?server=EU")

        # Save to single file
        print("Saving everything to combined_data.json...")
        with open("combined_data.json", "w", encoding="utf-8") as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
            
        print("Done. Saved all data to combined_data.json")

    finally:
        driver.quit()

if __name__ == "__main__":
    run_combined_scraper()