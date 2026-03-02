import sqlite3
import telebot
import os
import json
import io
from PIL import Image
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

# Uses the secure token from your .env file
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

DATABASE = "chat_clan.db"
DATA_FILE = "tanks_data.json"

# --- Database Functions ---
def setup_database():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            clan_name TEXT,
            lang TEXT DEFAULT 'en'
        )
        """)

def add_user(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

def add_clan(user_id, clan_name):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        # Ensure user exists first
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("UPDATE users SET clan_name=? WHERE user_id=?", (clan_name, user_id))

def get_clan_members(user_id):
    """Returns a list of all user_ids in the same clan as the given user."""
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        # 1. Find which clan the sender belongs to
        cur.execute("SELECT clan_name FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()

        if not result or not result[0]:
            return [] 

        clan_name = result[0]

        # 2. Find all members of that clan
        cur.execute("SELECT user_id FROM users WHERE clan_name = ?", (clan_name,))
        return [row[0] for row in cur.fetchall()]

# --- Tank Data & Image Functions ---
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
# --- Exp calculator funcion ---

def calculate_xp(skill_number, current_percentage):
    """
    Calculates the total XP required to reach a certain percentage 
    of a specific skill number.
    """
    if skill_number < 1:
        return 0

    
    base_xp_first_skill = 210064
    
    xp_previous_skills = base_xp_first_skill * (2**(skill_number - 1) - 1)
    

    xp_current_skill = base_xp_first_skill * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1)
    
    return round(xp_previous_skills + xp_current_skill)

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    welcome_text = (
        "Welcome!\n"
        "Use /clan <name> to join a group.\n"
        "Use /equipment <tank_name> or /crew <tank_name> to look up setups.\n"
        "USe /masagge after add to clan to send a massage\n"
        "Use /exp <Level_of_your_perk> <%of it >"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['clan'])
def set_clan(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /clan <name>")
        return

    clan_name = parts[1].lower()
    add_clan(message.chat.id, clan_name)
    bot.reply_to(message, f"You have joined the clan: **{clan_name}**", parse_mode="Markdown")

@bot.message_handler(commands=['masagge'])
def send_clan_message(message):
    # Split the command from the text
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /masagge <your message>")
        return

    text_to_send = parts[1]
    members = get_clan_members(message.chat.id)

    if not members:
        bot.reply_to(message, "You aren't in a clan yet! Use /clan first.")
        return

    count = 0
    for member_id in members:
        # Don't send the message back to the sender
        if member_id != message.chat.id:
            try:
                bot.send_message(member_id, f"📢 **Clan Message:**\n{text_to_send}", parse_mode="Markdown")
                count += 1
            except Exception as e:
                print(f"Could not send to {member_id}: {e}")

    bot.reply_to(message, f"Message sent to {count} clan members!")

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
@bot.message_handler(commands=['exp'])
def handle_exp_command(message): # Renamed to avoid conflict
    parts = message.text.split()

    # Check if the user provided enough arguments
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /exp <skill_number> <percentage>\nExample: /exp 2 50")
        return

    try:
        # Convert inputs to integers
        skill_num = int(parts[1])
        percentage = int(parts[2])
        
        total_needed = calculate_xp(skill_num, percentage)

        bot.send_message(message.chat.id, f"Total XP needed: {total_needed:,}")
    
    except ValueError:
        bot.reply_to(message, "Please provide valid numbers for skill and percentage.")
    except Exception as e:
        print(f"Error in exp calculation: {e}")
        bot.reply_to(message, "An error occurred while calculating XP.")
if __name__ == "__main__":
    setup_database()
    print("Bot is online and listening...")
    bot.infinity_polling()