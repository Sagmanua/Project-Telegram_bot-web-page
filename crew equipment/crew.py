import telebot
from PIL import Image
import io
import os
import json

bot = telebot.TeleBot('8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8') 
DATA_FILE = 'tanks_data.json'

def load_tank_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []

def process_and_combine_images(image_paths_list):
    """
    Takes a list of lists (rows of image paths) and returns a BytesIO object.
    For equipment, it's a list with one list inside: [[p1, p2, p3]]
    For crew, it's a list of lists: [[commander_perks], [driver_perks], ...]
    """
    try:
        grid_images = []
        max_cols = 0
        
        for row in image_paths_list:
            # Only keep paths that actually exist
            valid_images = [Image.open(p) for p in row if os.path.exists(p)]
            if valid_images:
                grid_images.append(valid_images)
                max_cols = max(max_cols, len(valid_images))

        if not grid_images:
            return None

        # Assume all perk/equipment icons are the same size based on the first one
        img_w, img_h = grid_images[0][0].size
        
        combined_img = Image.new('RGBA', (max_cols * img_w, len(grid_images) * img_h), (0, 0, 0, 0))

        for row_idx, row_imgs in enumerate(grid_images):
            for col_idx, img in enumerate(row_imgs):
                combined_img.paste(img, (col_idx * img_w, row_idx * img_h))

        img_byte_arr = io.BytesIO()
        combined_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception as e:
        print(f"Image Processing Error: {e}")
        return None

@bot.message_handler(commands=['equipment', 'crew'])
def handle_tank_commands(message):
    cmd = message.text.split()[0][1:] # 'equipment' or 'crew'
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        bot.reply_to(message, f"Usage: /{cmd} <tank_name>")
        return

    search_name = args[1].strip().lower()
    tanks = load_tank_data()
    tank_info = next((t for t in tanks if t.get('full_name', '').lower() == search_name), None)

    if not tank_info:
        bot.reply_to(message, f"Tank '{args[1]}' not found.")
        return

    image_grid = []
    
    if cmd == 'equipment':
        # Wrap in a list because equipment is just one row
        # Prepend directory if needed, e.g., 'images_equipment/' + path
        paths = [f"images_equipment/{p}" if not p.startswith('images') else p for p in tank_info.get('equipment', [])]
        image_grid = [paths]
    else:
        # Crew command: Build rows for each role
        roles = ['comander', 'driver', 'gunner', 'loader', 'radist']
        crew_data = tank_info.get('crew', {})
        image_grid = [crew_data[role] for role in roles if role in crew_data]

    result_bio = process_and_combine_images(image_grid)

    if result_bio:
        caption = f"{cmd.capitalize()} for {tank_info['full_name']}"
        bot.send_photo(message.chat.id, result_bio, caption=caption)
    else:
        bot.reply_to(message, f"Could not generate image for {cmd}. Check if files exist on server.")

print("Bot is listening...")
bot.infinity_polling()