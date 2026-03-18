import telebot
from PIL import Image
import io
import os
import json

# 1. Initialize your bot 
bot = telebot.TeleBot('8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8') 

# Path to your JSON file
DATA_FILE = 'tanks_data.json'
# Base path for equipment images (adjust if your images are in a subfolder)
IMAGE_BASE_PATH = 'images_equipment/'

def load_tank_data():
    """Loads tank data from the JSON file."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []

@bot.message_handler(commands=['equipment'])
def send_equipment_info(message):
    # Extract tank name from message (e.g., /equipment T-34)
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        bot.reply_to(message, "Please provide a tank name! Usage: /equipment <tank_name>")
        return

    search_name = args[1].strip().lower()
    tanks = load_tank_data()
    
    # Find the tank in the JSON data
    tank_info = next((t for t in tanks if t.get('full_name', '').lower() == search_name), None)

    if not tank_info or 'equipment' not in tank_info:
        bot.reply_to(message, f"Could not find equipment for tank: {args[1]}")
        return

    # The JSON contains only filenames (e.g., "podboi.png")
    # We prepend the directory path to find them locally
    equipment_filenames = tank_info['equipment']
    valid_paths = [os.path.join(IMAGE_BASE_PATH, fname) for fname in equipment_filenames]

    try:
        images = []
        for path in valid_paths:
            if os.path.exists(path):
                images.append(Image.open(path))
            else:
                # Optional: skip missing images or alert the user
                print(f"Warning: Image not found at {path}")

        if not images:
            bot.reply_to(message, "Equipment images are missing on the server.")
            return

        # Combine images horizontally
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)

        combined_img = Image.new('RGB', (total_width, max_height))

        x_offset = 0
        for img in images:
            combined_img.paste(img, (x_offset, 0))
            x_offset += img.width

        # Convert to byte array for Telegram
        img_byte_arr = io.BytesIO()
        combined_img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)

        # Send the final photo with a caption
        caption = f"Equipment for {tank_info['full_name']} (Tier {tank_info['tier']})"
        bot.send_photo(message.chat.id, img_byte_arr, caption=caption)

    except Exception as e:
        bot.reply_to(message, f"Error processing images: {e}")

print("Bot is listening...")
bot.infinity_polling()