import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_tomato_stats(tank_name):
    # Format the name for the URL (replace spaces with dashes)
    formatted_name = tank_name.lower().replace(" ", "-")
    
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")


    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Using the correct filter URL structure
        target_url = f"https://tomato.gg/tank-stats/?filter="
        print(f"Loading: {target_url}")
        driver.get(target_url)
        
        # Increased wait for the data to actually fetch
        wait = WebDriverWait(driver, 20)

        # We wait for the first table row that contains actual data
        # Tomato.gg rows usually contain the tank name in the first cell
        first_row = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
        
        # Give it a small buffer to ensure the numbers load into the cells
        time.sleep(2)
        
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