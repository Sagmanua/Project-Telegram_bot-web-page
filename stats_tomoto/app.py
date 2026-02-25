import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_tanksgg_stats(tank_name):
    formatted_name = tank_name.lower().replace(" ", "-")
    target_url = f"https://tanks.gg/tank/{formatted_name}"
    
    options = Options()
    options.add_argument("--headless") 
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        print(f"Connecting to: {target_url}")
        driver.get(target_url)
        
        # Increase wait time to 20 seconds
        wait = WebDriverWait(driver, 20)
        
        # Method: Target the 'Weaponry' section which we see in your screenshot
        # We wait for the text to appear inside the main content area
        wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Weaponry')]")))
        
        # Give it an extra second for the numbers to populate
        time.sleep(1)

        # Grab the main container that holds all the stat columns
        # Based on the site structure, stats are usually inside a main 'tank' or 'content' class
        # If 'stats' class fails, we grab the whole body content for that tank
        main_content = driver.find_element(By.TAG_NAME, "main")
        
        return main_content.text

    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        driver.quit()

if __name__ == "__main__":
    tank = input("Enter tank name (e.g., IS-7): ").strip()
    if tank:
        print(f"--- Scraping Tanks.gg Data ---")
        result = get_tanksgg_stats(tank)
        print("\n--- Results Found ---")
        print(result)