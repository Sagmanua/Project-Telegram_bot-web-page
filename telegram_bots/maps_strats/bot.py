import telebot
import json
import os

# 1. Configuration
API_TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
JSON_FILE = 'maps.json'
# Path to the folder where your images are stored
IMAGE_DIR = 'map_images' 

bot = telebot.TeleBot(API_TOKEN)

# 2. Load the JSON data
def load_maps():
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

MAPS_DATA = load_maps()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Send me a map name and I'll find the image for you.")

@bot.message_handler(func=lambda message: True)
def search_map(message):
    user_input = message.text.strip().lower()
    found_entry = None

    # Search logic: check every string in the "name" array
    for entry in MAPS_DATA:
        # Filter out empty strings and compare lowercase
        names_list = [n.lower() for n in entry.get("name", []) if n]
        
        if user_input in names_list:
            found_entry = entry
            break

    if found_entry:
        image_path = found_entry.get("root")
        
        # Check if the file actually exists on your server/computer
        if os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"Found: {user_input}")
        else:
            bot.reply_to(message, f"I found the map, but the file is missing at: {image_path}")
    else:
        bot.reply_to(message, "Map not found. Please check the spelling!")

# Start the bot
print("Bot is looking for maps...")
bot.infinity_polling()