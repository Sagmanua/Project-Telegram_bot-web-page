import time
import telebot
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def get_gunmarks_data(tank_name):
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get("https://poliroid.me/gunmarks/?server=EU")

    wait = WebDriverWait(driver, 15)

    # Wait for search input to appear
    search = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "input"))
    )

    search.clear()
    search.send_keys(tank_name)
    search.send_keys(Keys.ENTER)

    # Wait for table to load
    table = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )

    text = table.text

    driver.quit()
    return text

API_TOKEN = "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['tank'])
def send_tank_info(message):
        text_parts = message.text.split()
        tank_name = text_parts[1].lower()


        data = get_gunmarks_data(tank_name)
        bot.reply_to(message, data)


if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
