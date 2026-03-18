import sqlite3
import telebot
import os
import json
import io
import requests
import time
from PIL import Image
from dotenv import load_dotenv

# ---------------- CONFIG ----------------

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_TOKEN"
WG_APP_ID = os.getenv("WG_APP_ID") or "1c67a69b2758f598f6edab23ca7dbb7c"

DATABASE = "chat_clan.db"
DATA_FILE = "tanks_data.json"

bot = telebot.TeleBot(TOKEN)

# ---------------- DATABASE ----------------

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
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("UPDATE users SET clan_name=? WHERE user_id=?", (clan_name, user_id))

def get_clan_members(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT clan_name FROM users WHERE user_id=?", (user_id,))
        result = cur.fetchone()
        if not result or not result[0]:
            return []
        clan_name = result[0]
        cur.execute("SELECT user_id FROM users WHERE clan_name=?", (clan_name,))
        return [row[0] for row in cur.fetchall()]

# ---------------- WG API CLAN ONLINE ----------------

def get_clan_id_by_tag(tag):
    search_url = f"https://api.worldoftanks.eu/wot/clans/list/?application_id={WG_APP_ID}&search={tag}"
    try:
        response = requests.get(search_url).json()
        if response['status'] == 'ok' and response['data']:
            for clan in response['data']:
                if clan['tag'].upper() == tag.upper():
                    return clan['clan_id']
    except Exception as e:
        print(f"WG search error: {e}")
    return None

def get_active_members(clan_tag):
    clan_id = get_clan_id_by_tag(clan_tag)
    if not clan_id:
        return f"❌ <b>Clan [{clan_tag.upper()}] not found.</b>"

    clan_url = f"https://api.worldoftanks.eu/wot/clans/info/?application_id={WG_APP_ID}&clan_id={clan_id}"
    clan_data = requests.get(clan_url).json()

    if clan_data['status'] != 'ok':
        return "❌ WG API Error."

    members = clan_data['data'][str(clan_id)]['members']
    account_ids = ",".join([str(m['account_id']) for m in members])

    status_url = f"https://api.worldoftanks.eu/wot/account/info/?application_id={WG_APP_ID}&account_id={account_ids}&fields=nickname,last_battle_time"
    status_data = requests.get(status_url).json()

    active_list = []
    current_time = time.time()

    if status_data['status'] == 'ok':
        for acc_id, info in status_data['data'].items():
            if info and info.get('last_battle_time'):
                time_diff = current_time - info['last_battle_time']
                if time_diff < 7200:
                    minutes = int(time_diff // 60)
                    active_list.append(f"• <b>{info['nickname']}</b> ({minutes}m ago)")

    if not active_list:
        return f"No players from <b>[{clan_tag.upper()}]</b> active in last 2 hours."

    header = f"🔥 <b>Recently Active in [{clan_tag.upper()}]:</b>\n\n"
    return header + "\n".join(active_list)

# ---------------- TANK DATA ----------------

def load_tanks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_best_match(search_name):
    tanks = load_tanks()
    search_name = search_name.lower()
    for tank in tanks:
        if search_name in tank.get("full_name", "").lower():
            return tank
    return None

# ---------------- IMAGE PROCESSING ----------------

def process_and_combine_images(image_paths_list):
    try:
        grid_images = []
        max_cols = 0
        for row in image_paths_list:
            valid = []
            for p in row:
                if os.path.exists(p):
                    valid.append(Image.open(p))
            if valid:
                grid_images.append(valid)
                max_cols = max(max_cols, len(valid))

        if not grid_images:
            return None

        w, h = grid_images[0][0].size
        combined = Image.new('RGBA', (max_cols*w, len(grid_images)*h))

        for r, row in enumerate(grid_images):
            for c, img in enumerate(row):
                combined.paste(img, (c*w, r*h))

        bio = io.BytesIO()
        combined.save(bio, format='PNG')
        bio.seek(0)
        return bio
    except Exception as e:
        print(e)
        return None

# ---------------- XP CALCULATOR ----------------

def calculate_xp(skill_number, current_percentage):
    base = 210064
    xp_prev = base * (2**(skill_number - 1) - 1)
    xp_cur = base * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1)
    return round(xp_prev + xp_cur)

# ---------------- COMMANDS ----------------

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.reply_to(message,
        "Tank Assistant Online!\n\n"
        "Commands:\n"
        "/info <tank>\n"
        "/compare <tank1>, <tank2>\n"
        "/equipment <tank>\n"
        "/crew <tank>\n"
        "/clan <name>\n"
        "/masagge <text>\n"
        "/exp <skill> <percent>\n"
        "/clan_online <TAG>"
    )

@bot.message_handler(commands=['clan_online'])
def clan_online(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /clan_online PZE-H")
        return

    tag = parts[1]
    status_msg = bot.reply_to(message, f"Scanning {tag}...")
    result = get_active_members(tag)

    bot.edit_message_text(
        result,
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id,
        parse_mode="HTML"
    )

@bot.message_handler(commands=['exp'])
def handle_exp(message):
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /exp 2 50")
        return

    total = calculate_xp(int(parts[1]), int(parts[2]))
    bot.reply_to(message, f"XP needed: {total:,}")



# (Other handlers like /info, /compare, /equipment, /crew, /clan, /masagge remain unchanged)

# ---------------- RUN ----------------

if __name__ == "__main__":
    setup_database()
    print("Bot running...")
    bot.infinity_polling()