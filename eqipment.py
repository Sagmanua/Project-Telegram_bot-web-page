import telebot
from PIL import Image
import io
import os

# 1. Initialize your bot 
bot = telebot.TeleBot('8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8') 

# 2. Your JSON-style mapping of IDs to local file paths
# Note: I changed .ppg to .png assuming it was a typo
IMAGE_MAPPING = {
    "ebr": [
        "images_equipment/dosel.png", 
        "images_equipment/dosel.png", 
        "images_equipment/dosel.png"
    ],
}

@bot.message_handler(commands=['equipment'])
def send_equipment_info(message):
    # Split user input and ignore the first element (which is the "/equipment" command)
    args = message.text.split()[1:]
    
    if not args:
        bot.reply_to(message, "Please provide an equipment name! Usage: /equipment name")
        return

    # Gather all valid file paths based on the user's input
    valid_paths = []
    for arg in args:
        # We use .lower() to make it case-insensitive
        paths = IMAGE_MAPPING.get(arg.lower()) 
        if paths:
            valid_paths.extend(paths) # Flatten the lists into one single list of paths

    if not valid_paths:
        bot.reply_to(message, "Could not find any matching equipment images.")
        return

    try:
        # Open all images
        images = [Image.open(path) for path in valid_paths]

        # Calculate total width and the tallest height
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)

        # Create a new blank canvas
        # Note: If your PNGs have transparent backgrounds, use 'RGBA' instead of 'RGB'
        combined_img = Image.new('RGB', (total_width, max_height))

        # Paste them side-by-side
        x_offset = 0
        for img in images:
            combined_img.paste(img, (x_offset, 0))
            x_offset += img.width

        # Save to a byte stream so we don't have to save a file to disk
        img_byte_arr = io.BytesIO()
        
        # If you switch to an RGBA canvas for transparency, you must change format to 'PNG'
        combined_img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)

        # Send the final photo
        bot.send_photo(message.chat.id, img_byte_arr)

    except FileNotFoundError as e:
        # Catches the error if the image path doesn't actually exist on your machine
        bot.reply_to(message, f"File missing on server: {e.filename}")
    except Exception as e:
        bot.reply_to(message, f"Error processing images: {e}")

print("Bot is listening...")
bot.infinity_polling()