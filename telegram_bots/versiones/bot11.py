import sqlite3
import telebot
import os
import json
import io
import logging
import requests
import time
import threading
import feedparser
from datetime import datetime
from PIL import Image
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from rapidfuzz import process, fuzz
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

# Prioritize .env token, then fallback to hardcoded
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
WG_APP_ID = os.getenv("WG_APP_ID") or "1c67a69b2758f598f6edab23ca7dbb7c"
REGION = "eu"

DATABASE = "chat_clan.db"
DATA_FILE = "tanks_data.json"
COMBINED_DATA_FILE = "combined_data.json"
RSS_URL = f"https://worldoftanks.{REGION}/en/rss/news/"

# --- Modpack Configuration ---
SAVED_FILE_ID = "BQACAgIAAxkBAAIDlmm5TT9gsXXxtiJzkn9czeEsgyg6AAK9lQAC57jQSY8Ia8KsCLmgOgQ" 
WEBSITE_URL = "https://wgmods.net/46/"

bot = telebot.TeleBot(TOKEN)

# Set up basic logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

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
        cur.execute("""
        CREATE TABLE IF NOT EXISTS player_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT,
            battles INTEGER,
            wins INTEGER,
            damage INTEGER,
            frags INTEGER,
            snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        # RSS News tables
        cur.execute('CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)')
        cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')

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
        cur.execute("SELECT clan_name FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if not result or not result[0]:
            return [] 
        clan_name = result[0]
        cur.execute("SELECT user_id FROM users WHERE clan_name = ?", (clan_name,))
        return [row[0] for row in cur.fetchall()]

def save_player_stats(stats):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM player_statistics WHERE nickname = ?", (stats["nickname"],))
        exists = cur.fetchone()
        
        if not exists:
            cur.execute("""
            INSERT INTO player_statistics 
            (nickname, battles, wins, damage, frags)
            VALUES (?, ?, ?, ?, ?)
            """, (
                stats["nickname"],
                stats["battles"],
                stats["wins"],
                stats["avg_damage"] * stats["battles"],
                stats["frags"]
            ))

# --- RSS Database Logic ---
def add_subscriber(chat_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)', (chat_id,))

def remove_subscriber(chat_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))

def get_subscribers():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('SELECT chat_id FROM subscribers')
        return [row[0] for row in cur.fetchall()]

def get_last_link():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('SELECT value FROM settings WHERE key="last_link"')
        res = cur.fetchone()
        return res[0] if res else None

def set_last_link(link):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("last_link", ?)', (link,))

# --- Tank & Mastery Data Logic ---
def load_tanks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if data and isinstance(data, list) and data[0].get("tank_name") == "Tank Name":
            return data[1:]
        return data

def load_combined_data():
    try:
        with open(COMBINED_DATA_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"The file {COMBINED_DATA_FILE} was not found.")
        return {"mastery": [], "gunmarks": []}

COMBINED_DATA = load_combined_data()

def find_tank_data(category: str, tank_name: str):
    tank_list = [item.get("tank", "") for item in COMBINED_DATA.get(category, [])]
    if not tank_list: return None

    match = process.extractOne(tank_name, tank_list, scorer=fuzz.WRatio, score_cutoff=70)
    if match:
        best_match_name = match[0]
        for item in COMBINED_DATA.get(category, []):
            if item.get("tank") == best_match_name:
                return item
    return None

def get_best_match(search_name):
    tanks = load_tanks()
    search_name = search_name.lower().strip()
    partial_match = None
    for tank in tanks:
        fname = tank.get("full_name", "").lower()
        tname = tank.get("tank_name", "").lower()
        if fname == search_name or tname == search_name:
            return tank
        if (search_name in fname or search_name in tname) and not partial_match:
            partial_match = tank
    return partial_match

def get_tank_image_by_id(tank_id):
    url = f"https://api.worldoftanks.{REGION}/wot/encyclopedia/vehicles/"
    params = {"application_id": WG_APP_ID, "tank_id": tank_id}
    try:
        r = requests.get(url, params=params)
        data = r.json()
        if data["status"] == "ok":
            tank_data = data["data"].get(str(tank_id))
            if tank_data:
                return tank_data["images"]["big_icon"]
    except Exception as e:
        print("WG Image Error:", e)
    return None

# --- Bonus Codes Data ---
def get_active_codes():
    codes = {
        "Bonus Codes (Existing Players)": [
            ("HAPPYSTPT", "☘️ St. Patrick's Day Rewards (New)"),
            ("WOTEPT26", "🍱 Food-themed 2D Styles & Consumables"),
            ("OBKDMHNY26", "📦 Rare Bonus Container"),
            ("M4A376WBP14", "🛡️ Mission: Way to Victory"),
        ],
        "Invite Codes (New Accounts Only)": [
            ("REDDITFOREVER", "💰 500 Gold, Churchill III, 7 Days Premium"),
            ("TANKTASTIC", "🚜 T-127, 500 Gold, 7 Days Premium"),
            ("WOTGURU", "🚜 T14, 1000 Gold, 7 Days Premium"),
        ]
    }
    return codes

def escape_markdown(text):
    to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in to_escape:
        text = text.replace(char, f'\\{char}')
    return text

def extract_stats(tank):
    def clean_val(val, take_first=False):
        if not val or not isinstance(val, (str, int, float)): return 0.0
        val = str(val)
        if take_first and "/" in val: val = val.split("/")[0]
        clean_str = "".join(c for c in val if c.isdigit() or c == '.')
        try: return float(clean_str)
        except ValueError: return 0.0

    return {
        "full_name": tank.get("full_name", "Unknown"),
        "tier": tank.get("tier", "N/A"),
        "dpm": tank.get("Tank DPM", "0"),
        "dmg": tank.get("Dmg", "0"),
        "reload": tank.get("Reload", "0s"),
        "pen": tank.get("Pen", "0"),
        "velo": tank.get("Velo", "0"),
        "acc": tank.get("Acc", "0"),
        "aim": tank.get("Aim", "0s"),
        "dispersion": tank.get("Dispresion", "0"),
        "elevation": tank.get("DeP/Elev", "0"),
        "speed": tank.get("Speed", "0"),
        "traverse": tank.get("Traverse", "0"),
        "power": tank.get("Power", "0"),
        "pw": tank.get("P/W", "0"),
        "weight": tank.get("Weight", "0"),
        "hp": tank.get("Health", "0"),
        "vr": tank.get("VR", "0"),
        "n_dpm": clean_val(tank.get("Tank DPM")),
        "n_dmg": clean_val(tank.get("Dmg")),
        "n_reload": clean_val(tank.get("Reload")),
        "n_pen": clean_val(tank.get("Pen")),
        "n_velo": clean_val(tank.get("Velo")),
        "n_acc": clean_val(tank.get("Acc")),
        "n_aim": clean_val(tank.get("Aim")),
        "n_speed": clean_val(tank.get("Speed"), True),
        "n_traverse": clean_val(tank.get("Traverse")),
        "n_power": clean_val(tank.get("Power")),
        "n_pw": clean_val(tank.get("P/W")),
        "n_hp": clean_val(tank.get("Health")),
        "n_vr": clean_val(tank.get("VR"))
    }

# --- Image Processing ---
def process_and_combine_images(image_paths_list):
    try:
        grid_images = []
        max_cols = 0
        for row in image_paths_list:
            valid_images = []
            for p in row:
                full_path = p if p.startswith('images') else f"images_equipment/{p}"
                if os.path.exists(full_path):
                    valid_images.append(Image.open(full_path))
            
            if valid_images:
                grid_images.append(valid_images)
                max_cols = max(max_cols, len(valid_images))

        if not grid_images: return None

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

# --- Next Step Handlers ---
def process_tank_info(message):
    name = message.text.strip()
    tank = get_best_match(name)

    if not tank:
        bot.reply_to(message, "❌ Tank not found.")
        return

    s = extract_stats(tank)
    tank_id = tank.get("tank_id")
    image_url = get_tank_image_by_id(tank_id) if tank_id else None

    markup = InlineKeyboardMarkup()
    btn_equip = InlineKeyboardButton("⚙️ Equipment", callback_data=f"visual_equipment_{tank['full_name']}")
    btn_crew = InlineKeyboardButton("👨‍✈️ Crew Skills", callback_data=f"visual_crew_{tank['full_name']}")
    markup.row(btn_equip, btn_crew)

    response = (
        f"🛡️ *{s['full_name']}* (Tier {s['tier']})\n\n"
        f"🔥 DPM: `{s['dpm']}`\n"
        f"💥 Dmg: `{s['dmg']}`\n"
        f"⏱️ Reload: `{s['reload']}`\n"
        f"🎯 Pen: `{s['pen']}`\n"
        f"🚀 Velo: `{s['velo']} m/s`\n"
        f"🔬 Acc: `{s['acc']}`\n"
        f"⏲️ Aim: `{s['aim']}`\n"
        f"🌀 Disp: `{s['dispersion']}`\n"
        f"📐 Elev: `{s['elevation']}`\n"
        f"⚡ Speed: `{s['speed']} km/h`\n"
        f"🔄 Trav: `{s['traverse']}`\n"
        f"🐎 Power: `{s['power']}`\n"
        f"⚖️ P/W: `{s['pw']}`\n"
        f"🏋️ Wgt: `{s['weight']}`\n"
        f"❤️ HP: `{s['hp']}`\n"
        f"👁️ VR: `{s['vr']}m`"
    )

    if image_url:
        bot.send_photo(message.chat.id, image_url, caption=response, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=markup)

def process_tank_compare(message):
    parts = message.text.split(",")
    if len(parts) < 2:
        bot.reply_to(message, "💡 Format incorrect. Example: `AMX 30, T-34`. Type /start to try again.", parse_mode="Markdown")
        return

    t1 = get_best_match(parts[0].strip())
    t2 = get_best_match(parts[1].strip())
    
    if not t1 or not t2:
        bot.reply_to(message, "❌ Could not find one or both tanks. Please check the spelling and try again via /start.")
        return

    s1, s2 = extract_stats(t1), extract_stats(t2)

    def comp(v1, v2, raw1, raw2, higher_is_better=True):
        if v1 == v2: return f"{raw1} vs {raw2}"
        if higher_is_better:
            return f"*{raw1}* vs {raw2}" if v1 > v2 else f"{raw1} vs *{raw2}*"
        return f"*{raw1}* vs {raw2}" if v1 < v2 else f"{raw1} vs *{raw2}*"

    response = (
        f"🆚 *{s1['full_name']}* vs *{s2['full_name']}*\n\n"
        f"🎖️ Tier: `{s1['tier']} vs {s2['tier']}`\n"
        f"🔥 DPM: {comp(s1['n_dpm'], s2['n_dpm'], s1['dpm'], s2['dpm'])}\n"
        f"💥 Dmg: {comp(s1['n_dmg'], s2['n_dmg'], s1['dmg'], s2['dmg'])}\n"
        f"⏱️ Reload: {comp(s1['n_reload'], s2['n_reload'], s1['reload'], s2['reload'], False)}\n"
        f"🎯 Pen: {comp(s1['n_pen'], s2['n_pen'], s1['pen'], s2['pen'])}\n"
        f"🚀 Velo: {comp(s1['n_velo'], s2['n_velo'], s1['velo'], s2['velo'])} m/s\n"
        f"🔬 Acc: {comp(s1['n_acc'], s2['n_acc'], s1['acc'], s2['acc'], False)}\n"
        f"⏲️ Aim: {comp(s1['n_aim'], s2['n_aim'], s1['aim'], s2['aim'], False)}\n"
        f"🌀 Disp: `{s1['dispersion']} vs {s2['dispersion']}`\n"
        f"📐 Elev: `{s1['elevation']} vs {s2['elevation']}`\n"
        f"⚡ Speed: {comp(s1['n_speed'], s2['n_speed'], s1['speed'], s2['speed'])}\n"
        f"🔄 Trav: {comp(s1['n_traverse'], s2['n_traverse'], s1['traverse'], s2['traverse'])}\n"
        f"🐎 Power: {comp(s1['n_power'], s2['n_power'], s1['power'], s2['power'])}\n"
        f"⚖️ P/W: {comp(s1['n_pw'], s2['n_pw'], s1['pw'], s2['pw'])}\n"
        f"🏋️ Wgt: `{s1['weight']} vs {s2['weight']}`\n"
        f"❤️ HP: {comp(s1['n_hp'], s2['n_hp'], s1['hp'], s2['hp'])}\n"
        f"👁️ VR: {comp(s1['n_vr'], s2['n_vr'], s1['vr'], s2['vr'])}m"
    )
    
    try:
        bot.send_message(message.chat.id, response, parse_mode="Markdown")
    except Exception as e:
        print(f"Compare formatting error: {e}")
        bot.send_message(message.chat.id, "⚠️ " + response.replace("*", "").replace("`", ""))

def process_player_stats(message):
    player_name = message.text.strip()
    bot.send_chat_action(message.chat.id, 'typing') 
    
    try:
        stats = get_wot_stats(player_name)
        save_player_stats(stats)
        safe_nickname = stats['nickname'].replace("_", "\\_")

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📈 Check 7-Day Progress", callback_data=f"prog_7_{stats['nickname']}"))

        reply_text = (
            f"📊 **Stats for {safe_nickname}**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕹️ **Battles:** `{stats['battles']}`\n"
            f"🏆 **Wins:** `{stats['wins']}`\n"
            f"📈 **Winrate:** `{stats['winrate']}%`\n"
            f"💥 **Avg Damage:** `{stats['avg_damage']}`\n"
            f"💀 **Frags:** `{stats['frags']}`"
        )
        bot.reply_to(message, reply_text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e).replace('_', '\\_')}", parse_mode="Markdown")

def process_clan_online(message):
    tag = message.text.strip()
    status_msg = bot.reply_to(message, f"Scanning {tag}...")
    result = get_active_members(tag)
    bot.edit_message_text(result, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="HTML")

def process_exp_calc(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: `2 50`. Try /start again.")
        return
    try:
        skill_num, percentage = int(parts[0]), int(parts[1])
        total_needed = calculate_xp(skill_num, percentage)
        bot.send_message(message.chat.id, f"Total XP needed for skill {skill_num} at {percentage}%: **{total_needed:,}**", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "Please use numbers: `2 50`")

def process_moe_step(message, category):
    tank_name = message.text.strip()
    tank_data = find_tank_data(category, tank_name)

    if tank_data:
        values = [v for v in tank_data.get("values", []) if v]
        safe_tank_name = escape_markdown(tank_data['tank'])
        
        if category == "mastery":
            response = f"🏆 *Mastery Values for {safe_tank_name}*\n\n"
            labels = ["Class III", "Class II", "Class I", "Ace Tanker"]
        else:
            response = f"🎯 *Gun Mark Values for {safe_tank_name}*\n\n"
            labels = ["65% (1 Mark)", "85% (2 Marks)", "95% (3 Marks)", "100%"]
            
        for i, val in enumerate(values):
            label = labels[i] if i < len(labels) else f"Value {i+1}"
            response += f"• *{label}:* `{val}`\n"
            
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        cat_name = "Mastery" if category == "mastery" else "Gun Mark"
        bot.reply_to(message, f"❌ Sorry, I couldn't find {cat_name} data for '*{escape_markdown(tank_name)}*'.", parse_mode='Markdown')

# --- Math Functions ---
def calculate_xp(skill_number, current_percentage):
    if skill_number < 1: return 0
    base_xp_first_skill = 210064
    xp_previous_skills = base_xp_first_skill * (2**(skill_number - 1) - 1)
    xp_current_skill = base_xp_first_skill * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1)
    return round(xp_previous_skills + xp_current_skill)

# ---------------- WG API CLAN ONLINE ----------------
def get_clan_id_by_tag(tag):
    search_url = f"https://api.worldoftanks.{REGION}/wot/clans/list/?application_id={WG_APP_ID}&search={tag}"
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

    clan_url = f"https://api.worldoftanks.{REGION}/wot/clans/info/?application_id={WG_APP_ID}&clan_id={clan_id}"
    clan_data = requests.get(clan_url).json()

    if clan_data['status'] != 'ok':
        return "❌ WG API Error."

    members = clan_data['data'][str(clan_id)]['members']
    account_ids = ",".join([str(m['account_id']) for m in members])

    status_url = f"https://api.worldoftanks.{REGION}/wot/account/info/?application_id={WG_APP_ID}&account_id={account_ids}&fields=nickname,last_battle_time"
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('visual_'))
def handle_tank_visuals(call):
    parts = call.data.split('_')
    visual_type = parts[1]  
    tank_name = parts[2]    
    
    tank_info = get_best_match(tank_name)
    if not tank_info:
        bot.answer_callback_query(call.id, "❌ Tank data lost.")
        return

    bot.answer_callback_query(call.id, f"Generating {visual_type}...")
    
    image_grid = []
    if visual_type == 'equipment':
        paths = tank_info.get('equipment', [])
        image_grid = [paths]
    else:
        roles = ['comander', 'driver', 'gunner', 'loader', 'radist']
        crew_data = tank_info.get('crew', {})
        image_grid = [crew_data[role] for role in roles if role in crew_data]

    result_bio = process_and_combine_images(image_grid)
    
    if result_bio:
        bot.send_photo(
            call.message.chat.id, 
            result_bio, 
            caption=f"✅ {visual_type.capitalize()} setup for *{tank_info.get('full_name')}*",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(call.message.chat.id, f"⚠️ Could not generate {visual_type} image. Check server assets.")

def get_wot_stats(player_name):
    search_url = f"https://api.worldoftanks.{REGION}/wot/account/list/"
    search_params = {"application_id": WG_APP_ID, "search": player_name}
    
    r = requests.get(search_url, params=search_params)
    data = r.json().get("data", [])
    
    if not data:
        raise Exception(f"Player '{player_name}' not found.")
    
    account_id = data[0]["account_id"]
    nickname = data[0]["nickname"]

    info_url = f"https://api.worldoftanks.{REGION}/wot/account/info/"
    info_params = {"application_id": WG_APP_ID, "account_id": account_id}
    
    r = requests.get(info_url, params=info_params)
    player_data = r.json()["data"][str(account_id)]
    
    all_stats = player_data["statistics"]["all"]
    
    battles = all_stats["battles"]
    winrate = round(all_stats["wins"] / battles * 100, 2) if battles > 0 else 0
    avg_dmg = round(all_stats["damage_dealt"] / battles) if battles > 0 else 0

    return {
        "nickname": nickname,
        "battles": battles,
        "wins": all_stats["wins"],
        "winrate": winrate,
        "avg_damage": avg_dmg,
        "frags": all_stats["frags"]
    }

def get_stats_from_days_ago(nickname, days):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT battles, wins, damage, frags, snapshot_date
        FROM player_statistics
        WHERE nickname = ?
        AND snapshot_date <= datetime('now', ?)
        ORDER BY snapshot_date DESC
        LIMIT 1
        """, (nickname, f"-{days} days"))
        return cur.fetchone()

# --- Auto Checker Loop ---
def check_news_loop():
    while True:
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Checking WoT API/RSS feed...")

        try:
            feed = feedparser.parse(RSS_URL)
            if feed.entries:
                latest_entry = feed.entries[0]
                latest_link = latest_entry.link
                saved_link = get_last_link()

                if latest_link != saved_link:
                    if saved_link is not None:
                        print(f"[{now}] New news found: {latest_entry.title}")
                        users = get_subscribers()
                        safe_title = escape_markdown(latest_entry.title)
                        msg = f"🆕 *New WoT News!*\n\n*{safe_title}*\n{latest_link}"
                        
                        for user_id in users:
                            try:
                                bot.send_message(user_id, msg, parse_mode="Markdown")
                            except Exception as e:
                                print(f"Error sending to {user_id}: {e}")

                    set_last_link(latest_link)
                else:
                    print(f"[{now}] No change detected.")
        except Exception as e:
            print(f"[{now}] ERROR: {e}")

        time.sleep(300)

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    
    markup = InlineKeyboardMarkup(row_width=2)
    btn_tank = InlineKeyboardButton("🛡️ Tank Info", callback_data="menu_tank")
    btn_compare = InlineKeyboardButton("🆚 Compare Tanks", callback_data="menu_compare")
    btn_player = InlineKeyboardButton("📊 Player Stats", callback_data="menu_player")
    btn_clan = InlineKeyboardButton("🏰 Clan Tools", callback_data="menu_clan")
    btn_calc = InlineKeyboardButton("🧮 XP Calculator", callback_data="menu_calc")
    btn_moe = InlineKeyboardButton("🎖️ MoE / Mastery", callback_data="menu_moe")
    btn_news = InlineKeyboardButton("📰 WoT News", callback_data="menu_news")
    btn_codes = InlineKeyboardButton("🎁 Bonus Codes", callback_data="menu_codes")
    # NEW MODPACK BUTTON ADDED HERE
    btn_modpack = InlineKeyboardButton("📦 Modpack", callback_data="menu_modpack")
    
    markup.add(btn_tank, btn_compare, btn_player, btn_clan, btn_calc, btn_moe, btn_news, btn_codes, btn_modpack)

    welcome_text = (
        "👋 *Welcome to Tank Assistant!*\n\n"
        "I can help you find tank stats, check player progress, manage your clan, download mods, and find the latest rewards.\n"
        "👇 *Select an option below to get started:*"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# --- Modpack Command Handler ---
@bot.message_handler(commands=['modpack'])
def send_modpack_cmd(message):
    markup = InlineKeyboardMarkup(row_width=1)
    btn_download = InlineKeyboardButton("📥 Download from Telegram", callback_data="dl_tg")
    btn_website = InlineKeyboardButton("🌐 Go to Website", url=WEBSITE_URL)
    markup.add(btn_download, btn_website)
    
    bot.send_message(
        message.chat.id, 
        "<b>Aslain's WoT Modpack</b>\n\nChoose your preferred download method:", 
        parse_mode='HTML', 
        reply_markup=markup
    )

# --- Interactive Menu Callbacks ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_main_menu(call):
    chat_id = call.message.chat.id
    
    # 1. TANK INFO HANDLER
    if call.data == "menu_tank":
        msg = bot.send_message(chat_id, "🛡️ *Tank Info*\nType the name of the tank you want to look up (e.g., `IS-7`, `Leopard 1`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_tank_info)
        
    # 2. COMPARE TANKS HANDLER
    elif call.data == "menu_compare":
        msg = bot.send_message(chat_id, "🆚 *Compare Tanks*\nType two tanks separated by a comma (e.g., `AMX 30, T-34`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_tank_compare)
        
    # 3. PLAYER STATS HANDLER
    elif call.data == "menu_player":
        msg = bot.send_message(chat_id, "📊 *Player Stats*\nType the exact in-game nickname of the player:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_player_stats)
        
    # 4. CLAN TOOLS SUB-MENU
    elif call.data == "menu_clan":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🟢 Check Clan Online", callback_data="clan_online"))
        markup.add(InlineKeyboardButton("📢 Send Message to Clan", callback_data="clan_broadcast"))
        markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back"))
        bot.edit_message_text("🏰 *Clan Tools*\nChoose an action:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    
    # 5. XP CALCULATOR HANDLER
    elif call.data == "menu_calc":
        msg = bot.send_message(chat_id, "🧮 *XP Calculator*\nType the skill number and your current percentage separated by a space (e.g., `2 50`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_exp_calc)

    # 6. BONUS CODES HANDLER
    elif call.data == "menu_codes":
        response = (
            "🎁 *Active World of Tanks Codes*\n\n"
            "🔹 *Bonus Codes (Existing Players)*\n"
            "• `WOTEPT26` — Food-themed 2D Styles & Consumables\n"
            "• `HAPPYSTPT` — St. Patrick's Day Rewards\n"
            "• `OBKDMHNY26` — Rare Bonus Container\n\n"
            "🔹 *Invite Codes (New Accounts Only)*\n"
            "• `REDDITFOREVER` — 500 Gold, Churchill III, 7 Days Premium\n"
            "• `TANKTASTIC` — T-127, 500 Gold, 7 Days Premium\n\n"
            "🔗 [Redeem Code Here](https://eu.wargaming.net/shop/redeem/)\n"
            "_Tip: Tap a code to copy it!_"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back"))
        bot.edit_message_text(response, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown", disable_web_page_preview=True)

    # 7. NEW: MODPACK HANDLER
    elif call.data == "menu_modpack":
        markup = InlineKeyboardMarkup(row_width=1)
        btn_download = InlineKeyboardButton("📥 Download from Telegram", callback_data="dl_tg")
        btn_website = InlineKeyboardButton("🌐 Go to Website", url=WEBSITE_URL)
        btn_back = InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back")
        markup.add(btn_download, btn_website, btn_back)
        
        bot.edit_message_text(
            "<b>Aslain's WoT Modpack</b>\n\nChoose your preferred download method:", 
            chat_id, 
            call.message.message_id, 
            reply_markup=markup, 
            parse_mode='HTML'
        )

    # 8. BACK BUTTON HANDLER
    elif call.data == "menu_back":
        bot.delete_message(chat_id, call.message.message_id)
        start(call.message) 
        
    bot.answer_callback_query(call.id)

# --- Modpack Download Callback ---
@bot.callback_query_handler(func=lambda call: call.data == "dl_tg")
def handle_download(call):
    if "PASTE_YOUR_FILE_ID" in SAVED_FILE_ID:
        bot.answer_callback_query(call.id, "Error: File ID not set in code.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "Sending file...")
    
    try:
        bot.send_document(
            call.message.chat.id, 
            SAVED_FILE_ID, 
            caption="✅ <b>Aslain's Modpack Installer</b>\nReady to install.",
            parse_mode='HTML'
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Failed to send: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('news_sub_'))
def handle_news_subscriptions(call):
    chat_id = call.message.chat.id
    if call.data == "news_sub_on":
        add_subscriber(chat_id)
        bot.answer_callback_query(call.id, "✅ Subscribed to News!")
        bot.send_message(chat_id, "✅ You are now subscribed to World of Tanks news updates.")
    elif call.data == "news_sub_off":
        remove_subscriber(chat_id)
        bot.answer_callback_query(call.id, "❌ Unsubscribed from News")
        bot.send_message(chat_id, "❌ You have unsubscribed. You will no longer receive news updates.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('moe_cat_'))
def handle_moe_category(call):
    category = call.data.split('_')[2] 
    cat_name = "Mastery" if category == 'mastery' else "Gunmarks (MoE)"
    
    msg = bot.send_message(call.message.chat.id, f"Type the tank name for *{cat_name}* (e.g., `Tiger I`):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: process_moe_step(m, category))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'clan_online')
def handle_clan_online_btn(call):
    msg = bot.send_message(call.message.chat.id, "🟢 Type the clan tag you want to scan (e.g., `PZE-H`):")
    bot.register_next_step_handler(msg, process_clan_online)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'clan_broadcast')
def handle_clan_broadcast_btn(call):
    msg = bot.send_message(
        call.message.chat.id, 
        "📢 *Clan Broadcast*\n\nPlease **reply to the message** you want to send to everyone in your clan with the word `send`, or just type your message here now to send it as text.", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_clan_message_logic)
    bot.answer_callback_query(call.id)

# --- Command Handlers ---
@bot.message_handler(commands=['news_on'])
def command_subscribe(message):
    add_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "✅ Subscribed to World of Tanks news!")

@bot.message_handler(commands=['news_off'])
def command_unsubscribe(message):
    remove_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "❌ Unsubscribed. You will no longer receive news.")

@bot.message_handler(commands=["info"])
def handle_info(message):
    name = message.text.replace("/info", "").strip()
    tank = get_best_match(name)

    if not tank:
        bot.reply_to(message, "❌ Tank not found.")
        return

    s = extract_stats(tank)
    tank_id = tank.get("tank_id")
    image_url = get_tank_image_by_id(tank_id) if tank_id else None

    response = (
        f"🛡️ *{s['full_name']}* (Tier {s['tier']})\n\n"
        f"🔥 DPM: `{s['dpm']}`\n"
        f"💥 Damage: `{s['dmg']}`\n"
        f"⏱ Reload: `{s['reload']}`\n"
        f"🎯 Pen: `{s['pen']}`\n"
        f"⚡ Speed: `{s['speed']} km/h`\n"
        f"❤️ HP: `{s['hp']}`"
    )

    if image_url:
        bot.send_photo(message.chat.id, image_url, caption=response, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=["compare"])
def handle_compare(message):
    parts = message.text.replace("/compare", "").split(",")
    if len(parts) < 2:
        bot.reply_to(message, "💡 Usage: `/compare AMX 30, T-34`", parse_mode="Markdown")
        return

    t1 = get_best_match(parts[0].strip())
    t2 = get_best_match(parts[1].strip())
    if not t1 or not t2:
        bot.reply_to(message, "❌ Could not find both tanks.")
        return

    s1, s2 = extract_stats(t1), extract_stats(t2)

    def comp(v1, v2, raw1, raw2, higher_is_better=True):
        if v1 == v2: return f"{raw1} vs {raw2}"
        if higher_is_better:
            return f"*{raw1}* vs {raw2}" if v1 > v2 else f"{raw1} vs *{raw2}*"
        return f"*{raw1}* vs {raw2}" if v1 < v2 else f"{raw1} vs *{raw2}*"

    response = (
        f"🆚 *{s1['full_name']}* vs *{s2['full_name']}*\n\n"
        f"🎖️ Tier: `{s1['tier']} vs {s2['tier']}`\n"
        f"🔥 DPM: {comp(s1['n_dpm'], s2['n_dpm'], s1['dpm'], s2['dpm'])}\n"
        f"💥 Dmg: {comp(s1['n_dmg'], s2['n_dmg'], s1['dmg'], s2['dmg'])}\n"
        f"⏱️ Reload: {comp(s1['n_reload'], s2['n_reload'], s1['reload'], s2['reload'], False)}\n"
        f"🎯 Pen: {comp(s1['n_pen'], s2['n_pen'], s1['pen'], s2['pen'])}\n"
        f"🚀 Velo: {comp(s1['n_velo'], s2['n_velo'], s1['velo'], s2['velo'])} m/s\n"
        f"🔬 Acc: {comp(s1['n_acc'], s2['n_acc'], s1['acc'], s2['acc'], False)}\n"
        f"⏲️ Aim: {comp(s1['n_aim'], s2['n_aim'], s1['aim'], s2['aim'], False)}\n"
        f"🌀 Disp: `{s1['dispersion']} vs {s2['dispersion']}`\n"
        f"📐 Elev: `{s1['elevation']} vs {s2['elevation']}`\n"
        f"⚡ Speed: {comp(s1['n_speed'], s2['n_speed'], s1['speed'], s2['speed'])}\n"
        f"🔄 Trav: {comp(s1['n_traverse'], s2['n_traverse'], s1['traverse'], s2['traverse'])}\n"
        f"🐎 Power: {comp(s1['n_power'], s2['n_power'], s1['power'], s2['power'])}\n"
        f"⚖️ P/W: {comp(s1['n_pw'], s2['n_pw'], s1['pw'], s2['pw'])}\n"
        f"🏋️ Wgt: `{s1['weight']} vs {s2['weight']}`\n"
        f"❤️ HP: {comp(s1['n_hp'], s2['n_hp'], s1['hp'], s2['hp'])}\n"
        f"👁️ VR: {comp(s1['n_vr'], s2['n_vr'], s1['vr'], s2['vr'])}m"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

def process_clan_message_logic(message):
    sender_id = message.from_user.id
    members = get_clan_members(sender_id)

    if not members:
        bot.reply_to(message, "❌ You aren't in a clan yet! Use `/clan <name>` first to join one.")
        return

    count = 0
    target_message = message.reply_to_message if message.reply_to_message else message
    status_msg = bot.reply_to(message, "🚀 Sending broadcast...")

    for member_id in members:
        if member_id != sender_id:
            try:
                bot.copy_message(
                    chat_id=member_id,
                    from_chat_id=target_message.chat.id,
                    message_id=target_message.message_id
                )
                count += 1
            except Exception:
                continue

    bot.edit_message_text(
        f"✅ **Broadcast Complete**\nMessage sent to {count} clan members!",
        chat_id=status_msg.chat.id,
        message_id=status_msg.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['equipment', 'crew'])
def handle_visual_commands(message):
    cmd = message.text.split()[0][1:]
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, f"Usage: /{cmd} <tank_name>")
        return

    tank_info = get_best_match(args[1])
    if not tank_info:
        bot.reply_to(message, f"Tank '{args[1]}' not found.")
        return

    image_grid = []
    if cmd == 'equipment':
        paths = tank_info.get('equipment', [])
        image_grid = [paths]
    else:
        roles = ['comander', 'driver', 'gunner', 'loader', 'radist']
        crew_data = tank_info.get('crew', {})
        image_grid = [crew_data[role] for role in roles if role in crew_data]

    result_bio = process_and_combine_images(image_grid)
    if result_bio:
        bot.send_photo(message.chat.id, result_bio, caption=f"{cmd.capitalize()} for {tank_info.get('full_name')}")
    else:
        bot.reply_to(message, f"Could not generate image. Ensure asset files are on the server.")

@bot.message_handler(commands=['exp'])
def handle_exp_command(message):
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /exp <skill_number> <percentage>")
        return
    try:
        skill_num, percentage = int(parts[1]), int(parts[2])
        total_needed = calculate_xp(skill_num, percentage)
        bot.send_message(message.chat.id, f"Total XP needed for skill {skill_num} at {percentage}%: **{total_needed:,}**", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "Please use numbers: `/exp 2 50`")

@bot.message_handler(commands=['clan_online'])
def clan_online(message):
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /clan_online PZE-H")
        return
    tag = parts[1]
    status_msg = bot.reply_to(message, f"Scanning {tag}...")
    result = get_active_members(tag)
    bot.edit_message_text(result, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="HTML")

@bot.message_handler(commands=['mastery'])
def handle_mastery(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Please provide a tank name. Example: `/mastery Tiger I`", parse_mode='Markdown')
        return
    message.text = parts[1]
    process_moe_step(message, "mastery")

@bot.message_handler(commands=['gunmark'])
def handle_gunmark(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Please provide a tank name. Example: `/gunmark M103`", parse_mode='Markdown')
        return
    message.text = parts[1]
    process_moe_step(message, "gunmarks")

@bot.message_handler(commands=['player_stats'])
def stats_command(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: /player_stats <player_name>")
            return

        player_name = args[1]
        bot.send_chat_action(message.chat.id, 'typing') 
        
        stats = get_wot_stats(player_name)
        save_player_stats(stats)
        safe_nickname = stats['nickname'].replace("_", "\\_")

        reply_text = (
            f"📊 **Stats for {safe_nickname}**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕹️ **Battles:** `{stats['battles']}`\n"
            f"🏆 **Wins:** `{stats['wins']}`\n"
            f"📈 **Winrate:** `{stats['winrate']}%`\n"
            f"💥 **Avg Damage:** `{stats['avg_damage']}`\n"
            f"💀 **Frags:** `{stats['frags']}`"
        )
        bot.reply_to(message, reply_text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {escape_markdown(str(e))}", parse_mode="Markdown")

@bot.message_handler(commands=['progress'])
def progress_command(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Usage: /progress <player_name> <days>")
            return

        player_name = args[1]
        days = int(args[2])

        current = get_wot_stats(player_name)
        old = get_stats_from_days_ago(current["nickname"], days)

        if not old:
            bot.reply_to(message, f"❓ No data found for {escape_markdown(player_name)} from {days} days ago.")
            return

        old_battles, old_wins, old_damage, old_frags, old_date = old

        diff_battles = current["battles"] - old_battles
        diff_wins = current["wins"] - old_wins
        diff_damage = (current["avg_damage"] * current["battles"]) - old_damage
        diff_frags = current["frags"] - old_frags

        if diff_battles > 0:
            session_winrate = round((diff_wins / diff_battles) * 100, 2)
            session_avg_dmg = round(diff_damage / diff_battles)
        else:
            session_winrate = 0
            session_avg_dmg = 0

        safe_name = escape_markdown(current['nickname'])
        safe_date = escape_markdown(str(old_date))

        reply = (
            f"📈 **Progress for {safe_name}**\n"
            f"🗓️ *Last {days} days (since {safe_date})*\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕹️ **Battles:** +{diff_battles}\n"
            f"🏆 **Session Winrate:** {session_winrate}%\n"
            f"💥 **Session Avg Dmg:** {session_avg_dmg}\n"
            f"💀 **Frags:** +{diff_frags}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✨ *Current Winrate: {current['winrate']}%*"
        )
        bot.reply_to(message, reply, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {escape_markdown(str(e))}")

if __name__ == "__main__":
    setup_database()
    
    # Start the RSS checker in a background thread
    threading.Thread(target=check_news_loop, daemon=True).start()
    
    logging.info("Bot started and RSS loop running...")
    bot.infinity_polling()