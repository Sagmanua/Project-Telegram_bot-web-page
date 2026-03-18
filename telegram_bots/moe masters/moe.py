import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def get_all_gunmarks():

    options = Options()
    # DO NOT use headless so you can see it
    # options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    print("Opening website...")
    driver.get("https://poliroid.me/gunmarks/?server=EU")

    time.sleep(5)  # wait for table to load

    print("Reading table rows...")

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    tanks = []

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")

        if len(cols) >= 6:
            tank_name = cols[3].text   # Tank name
            mark2 = cols[4].text       # 85%
            mark3 = cols[5].text
            mark5 = cols[6].text  

            tanks.append({
                "tank": tank_name,
                "values": [ mark2, mark3,mark5,]
            })

            print(tank_name,  mark2, mark3,mark5)  # Console output

    print("Saving JSON...")

    with open("gunmarks.json", "w", encoding="utf-8") as f:
        json.dump(tanks, f, indent=2, ensure_ascii=False)

    driver.quit()

    print("Done. Saved", len(tanks), "tanks")


get_all_gunmarks()