import json
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

JSON_FILE = "moe_mastery.json"
API_TOKEN = "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"

bot = telebot.TeleBot(API_TOKEN)


def load_database():
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_database(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=4)


def create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


def get_gunmarks_data(tank_name):
    driver = create_driver()

    driver.get("https://poliroid.me/gunmarks/?server=EU")

    wait = WebDriverWait(driver, 15)

    search = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "input"))
    )

    search.clear()
    search.send_keys(tank_name)
    search.send_keys(Keys.ENTER)

    table = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )

    text = table.text

    driver.quit()

    return text


def get_mastery_data(tank_name):
    driver = create_driver()

    driver.get("https://poliroid.me/mastery/?server=EU")

    wait = WebDriverWait(driver, 15)

    search = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "input"))
    )

    search.clear()
    search.send_keys(tank_name)
    search.send_keys(Keys.ENTER)

    table = wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )

    text = table.text

    driver.quit()

    return text


def get_tank_data(tank_name):
    database = load_database()

    if tank_name in database:
        return database[tank_name]

    gunmarks = get_gunmarks_data(tank_name)
    mastery = get_mastery_data(tank_name)

    database[tank_name] = {
        "gunmarks": gunmarks,
        "mastery": mastery
    }

    save_database(database)

    return database[tank_name]


@bot.message_handler(commands=['moe'])
def moe_command(message):
    try:
        tank_name = message.text.split(maxsplit=1)[1].lower()
    except:
        bot.reply_to(message, "Usage: /moe tank_name")
        return

    data = get_tank_data(tank_name)

    bot.reply_to(message, f"Gun Marks for {tank_name}:\n\n{data['gunmarks']}")


@bot.message_handler(commands=['mastery'])
def mastery_command(message):
    try:
        tank_name = message.text.split(maxsplit=1)[1].lower()
    except:
        bot.reply_to(message, "Usage: /mastery tank_name")
        return

    data = get_tank_data(tank_name)

    bot.reply_to(message, f"Mastery for {tank_name}:\n\n{data['mastery']}")


if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()