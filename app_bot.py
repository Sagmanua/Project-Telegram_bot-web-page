import os
import json
import io
import logging
import requests
import time
import threading
import feedparser
import sqlite3
from datetime import datetime
from PIL import Image

# Flask Imports
from flask import Flask, redirect, url_for, request, flash, render_template
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

# Bot Imports
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from rapidfuzz import process, fuzz
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

# Bot Config
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
WG_APP_ID = os.getenv("WG_APP_ID") or "1c67a69b2758f598f6edab23ca7dbb7c"
REGION = "eu"

DATABASE = "chat_clan.db"
DATA_FILE = "tanks_data.json"
COMBINED_DATA_FILE = "combined_data.json"
RSS_URL = f"https://worldoftanks.{REGION}/en/rss/news/"
MAPS_JSON_FILE = 'maps.json'

SAVED_FILE_ID = "BQACAgIAAxkBAAIDlmm5TT9gsXXxtiJzkn9czeEsgyg6AAK9lQAC57jQSY8Ia8KsCLmgOgQ" 
WEBSITE_URL = "https://wgmods.net/46/"

bot = telebot.TeleBot(TOKEN)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Flask Config
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
# Dynamically get the absolute path to the database to ensure Flask and Bot look at the same file
db_path = os.path.abspath(DATABASE)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024 

db = SQLAlchemy(app)

# --- Localization Strings ---
STRINGS = {
    'en': {
        'welcome': "👋 *Welcome to Tank Assistant!\n"
        "I can help you find tank stats, check player progress, manage your clan, download mods, and find the latest rewards.\n"
        "👇 Select an option below to get started:*",
        'btn_tank': "🛡️ Tank Info",
        'btn_compare': "🆚 Compare",
        'btn_player': "📊 Player Stats",
        'btn_clan': "🏰 Clan Tools",
        'btn_calc': "🧮 XP Calc",
        'btn_moe': "🎖️ MoE/Mastery",
        'btn_news': "📰 News",
        'btn_codes': "🎁 Codes",
        'btn_modpack': "📦 Modpack",
        'btn_maps': "🗺️ Maps",
        'btn_settings': "⚙️ Settings",
        'choose_lang': "⚙️ *Settings*\n\nSelect your preferred language:",
        'lang_updated': "✅ Language updated to English 🇬🇧"
    },
    'ru': {
        'welcome': "👋 *Добро пожаловать в Tank Assistant!*",
        'btn_tank': "🛡️ Инфо Танка",
        'btn_compare': "🆚 Сравнение",
        'btn_player': "📊 Статистика",
        'btn_clan': "🏰 Клан",
        'btn_calc': "🧮 Калькулятор XP",
        'btn_moe': "🎖️ Отметки/Мастер",
        'btn_news': "📰 Новости",
        'btn_codes': "🎁 Бонус Коды",
        'btn_modpack': "📦 Модпак",
        'btn_maps': "🗺️ Карты",
        'btn_settings': "⚙️ Настройки",
        'choose_lang': "⚙️ *Настройки*\n\nВыберите язык:",
        'lang_updated': "✅ Язык изменен на Русский 🇷🇺"
    },
    'ua': {
        'welcome': "👋 *Ласкаво просимо до Tank Assistant!*",
        'btn_tank': "🛡️ Інфо Танка",
        'btn_compare': "🆚 Порівняння",
        'btn_player': "📊 Статистика",
        'btn_clan': "🏰 Клан",
        'btn_calc': "🧮 Калькулятор XP",
        'btn_moe': "🎖️ Відмітки/Майстер",
        'btn_news': "📰 Новини",
        'btn_codes': "🎁 Бонус Коди",
        'btn_modpack': "📦 Модпак",
        'btn_maps': "🗺️ Карти",
        'btn_settings': "⚙️ Налаштування",
        'choose_lang': "⚙️ *Налаштування*\n\nОберіть мову:",
        'lang_updated': "✅ Мову змінено на Українську 🇺🇦"
    }
}

# --- Database Setup Functions ---
def setup_database():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, clan_name TEXT, lang TEXT DEFAULT 'en')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS player_statistics (id INTEGER PRIMARY KEY AUTOINCREMENT, nickname TEXT, battles INTEGER, wins INTEGER, damage INTEGER, frags INTEGER, snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute('CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)')
        cur.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')

# Ensure DB and tables exist before Flask reflects them
setup_database()

# --- 1. Dynamic Table Reflection (Flask) ---
with app.app_context():
    db.engine.connect() 
    metadata = MetaData()
    metadata.reflect(bind=db.engine)
    
    reflected_models = {}
    for table_name, table_obj in metadata.tables.items():
        if table_name == 'sqlite_sequence':
            continue
        class_name = table_name.capitalize().replace("_", "")
        model_class = type(class_name, (db.Model,), {'__table__': table_obj})
        reflected_models[table_name] = model_class

# --- 2. Custom View for Editing JSON Files (Flask Admin) ---
class JsonAdminView(BaseView):
    def __init__(self, file_path, name, **kwargs):
        self.file_path = file_path
        super(JsonAdminView, self).__init__(name=name, **kwargs)

    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if request.method == 'POST':
            if 'json_file' in request.files and request.files['json_file'].filename != '':
                file = request.files['json_file']
                try:
                    data = json.load(file)
                    with open(self.file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    flash(f'File uploaded and {self.name} updated!', 'success')
                except Exception as e:
                    flash(f'Upload Error: {str(e)}', 'error')
            elif request.form.get('json_data'):
                try:
                    json_dict = json.loads(request.form.get('json_data'))
                    with open(self.file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_dict, f, indent=4, ensure_ascii=False)
                    flash(f'Updated {self.name} via text!', 'success')
                except Exception as e:
                    flash(f'JSON Error: {str(e)}', 'error')

        content = ""
        file_size_mb = 0
        if os.path.exists(self.file_path):
            file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            if file_size_mb < 1.0:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    try:
                        content = json.dumps(json.load(f), indent=4, ensure_ascii=False)
                    except:
                        content = "{}"
            else:
                content = "// File is too large for the text area. Use the Upload feature."
            
        return self.render('admin/json_edit.html', content=content, filename=self.name, size=round(file_size_mb, 2))

# --- 3. Setup Admin Panel (Flask) ---
admin = Admin(app, name='Clan Project Admin')
for table_name, model in reflected_models.items():
    view_class = type(f"{table_name}View", (ModelView,), {'column_display_pk': True})
    admin.add_view(view_class(model, db.session, name=f"DB: {table_name}", category="Database"))

admin.add_view(JsonAdminView(DATA_FILE, 'Tanks', endpoint='tanks_json', category="JSON Files"))
admin.add_view(JsonAdminView(MAPS_JSON_FILE, 'Maps', endpoint='maps_json', category="JSON Files"))
admin.add_view(JsonAdminView(COMBINED_DATA_FILE, 'Combined', endpoint='combined_json', category="JSON Files"))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin_redirect')
def index():
    return redirect(url_for('admin.index'))

# --- Bot Helper Functions ---
def add_user(user_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))

def add_clan(user_id, clan_name):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE users SET clan_name=? WHERE user_id=?", (clan_name, user_id))

def get_clan_members(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT clan_name FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()
        if not result or not result[0]: return []
        cur.execute("SELECT user_id FROM users WHERE clan_name = ?", (result[0],))
        return [row[0] for row in cur.fetchall()]

def set_user_language(user_id, lang_code):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang_code, user_id))

def get_user_language(user_id):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT lang FROM users WHERE user_id=?", (user_id,))
        res = cur.fetchone()
        return res[0] if res else 'en'

def save_player_stats(stats):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM player_statistics WHERE nickname = ?", (stats["nickname"],))
        if not cur.fetchone():
            cur.execute("""INSERT INTO player_statistics (nickname, battles, wins, damage, frags)
                           VALUES (?, ?, ?, ?, ?)""", 
                        (stats["nickname"], stats["battles"], stats["wins"], stats["avg_damage"] * stats["battles"], stats["frags"]))

def load_maps_data():
    try:
        with open(MAPS_JSON_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return []

MAPS_DATA = load_maps_data()

def add_subscriber(chat_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)', (chat_id,))

def remove_subscriber(chat_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))

def get_subscribers():
    with sqlite3.connect(DATABASE) as conn:
        return [row[0] for row in conn.execute('SELECT chat_id FROM subscribers').fetchall()]

def get_last_link():
    with sqlite3.connect(DATABASE) as conn:
        res = conn.execute('SELECT value FROM settings WHERE key="last_link"').fetchone()
        return res[0] if res else None

def set_last_link(link):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("last_link", ?)', (link,))

def load_tanks():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data[1:] if data and isinstance(data, list) and data[0].get("tank_name") == "Tank Name" else data

def load_combined_data():
    try:
        with open(COMBINED_DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return {"mastery": [], "gunmarks": []}

COMBINED_DATA = load_combined_data()

def find_tank_data(category: str, tank_name: str):
    tank_list = [item.get("tank", "") for item in COMBINED_DATA.get(category, [])]
    if not tank_list: return None
    match = process.extractOne(tank_name, tank_list, scorer=fuzz.WRatio, score_cutoff=70)
    if match:
        for item in COMBINED_DATA.get(category, []):
            if item.get("tank") == match[0]: return item
    return None

def get_best_match(search_name):
    tanks = load_tanks()
    search_name = search_name.lower().strip()
    partial_match = None
    for tank in tanks:
        fname = tank.get("full_name", "").lower()
        tname = tank.get("tank_name", "").lower()
        if fname == search_name or tname == search_name: return tank
        if (search_name in fname or search_name in tname) and not partial_match: partial_match = tank
    return partial_match

def get_tank_image_by_id(tank_id):
    url = f"https://api.worldoftanks.{REGION}/wot/encyclopedia/vehicles/"
    try:
        r = requests.get(url, params={"application_id": WG_APP_ID, "tank_id": tank_id})
        data = r.json()
        if data["status"] == "ok" and data["data"].get(str(tank_id)):
            return data["data"][str(tank_id)]["images"]["big_icon"]
    except Exception as e: print("WG Image Error:", e)
    return None
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
    for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
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

# --- Next Step Logic ---
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
    bot.edit_message_text(get_active_members(tag), chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode="HTML")

def process_exp_calc(message):
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: `2 50`. Try /start again.")
    try:
        total_needed = calculate_xp(int(parts[0]), int(parts[1]))
        bot.send_message(message.chat.id, f"Total XP needed for skill {parts[0]} at {parts[1]}%: **{total_needed:,}**", parse_mode="Markdown")
    except ValueError: bot.reply_to(message, "Please use numbers: `2 50`")

def process_moe_step(message, category):
    tank_data = find_tank_data(category, message.text.strip())
    if not tank_data: return bot.reply_to(message, f"❌ Sorry, I couldn't find data for '*{escape_markdown(message.text.strip())}*'.", parse_mode='Markdown')

    values, safe_tank_name = [v for v in tank_data.get("values", []) if v], escape_markdown(tank_data['tank'])
    labels = ["Class III", "Class II", "Class I", "Ace Tanker"] if category == "mastery" else ["65% (1 Mark)", "85% (2 Marks)", "95% (3 Marks)", "100%"]
    
    response = f"{'🏆 *Mastery' if category == 'mastery' else '🎯 *Gun Mark'} Values for {safe_tank_name}*\n\n"
    for i, val in enumerate(values): response += f"• *{labels[i] if i < len(labels) else f'Value {i+1}'}:* `{val}`\n"
    bot.reply_to(message, response, parse_mode='Markdown')

def process_map_search(message):
    user_input = message.text.strip().lower()
    found_entry = next((e for e in MAPS_DATA if user_input in [n.lower() for n in e.get("name", []) if n]), None)
    if not found_entry: return bot.reply_to(message, "❌ Map not found. Please check the spelling!")
    
    image_path = found_entry.get("root")
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as photo: bot.send_photo(message.chat.id, photo, caption=f"🗺️ <b>Map Found:</b> {user_input.title()}", parse_mode="HTML")
    else: bot.reply_to(message, f"❌ Image missing at: <code>{image_path}</code>", parse_mode="HTML")

# --- WG API & Logic ---
def calculate_xp(skill_number, current_percentage):
    if skill_number < 1: return 0
    base_xp_first_skill = 210064
    xp_previous_skills = base_xp_first_skill * (2**(skill_number - 1) - 1)
    xp_current_skill = base_xp_first_skill * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1)
    return round(xp_previous_skills + xp_current_skill)

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

def get_wot_stats(player_name):
    r = requests.get(f"https://api.worldoftanks.{REGION}/wot/account/list/", params={"application_id": WG_APP_ID, "search": player_name})
    data = r.json().get("data", [])
    if not data: raise Exception(f"Player '{player_name}' not found.")
    
    account_id, nickname = data[0]["account_id"], data[0]["nickname"]
    r = requests.get(f"https://api.worldoftanks.{REGION}/wot/account/info/", params={"application_id": WG_APP_ID, "account_id": account_id})
    stats = r.json()["data"][str(account_id)]["statistics"]["all"]
    
    return {
        "nickname": nickname, "battles": stats["battles"], "wins": stats["wins"],
        "winrate": round(stats["wins"] / stats["battles"] * 100, 2) if stats["battles"] > 0 else 0,
        "avg_damage": round(stats["damage_dealt"] / stats["battles"]) if stats["battles"] > 0 else 0, "frags": stats["frags"]
    }

def get_stats_from_days_ago(nickname, days):
    with sqlite3.connect(DATABASE) as conn:
        return conn.execute("""SELECT battles, wins, damage, frags, snapshot_date FROM player_statistics WHERE nickname = ? AND snapshot_date <= datetime('now', ?) ORDER BY snapshot_date DESC LIMIT 1""", (nickname, f"-{days} days")).fetchone()

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
    lang = get_user_language(message.chat.id)
    txt = STRINGS.get(lang, STRINGS['en'])
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(txt['btn_tank'], callback_data="menu_tank"),
        InlineKeyboardButton(txt['btn_compare'], callback_data="menu_compare"),
        InlineKeyboardButton(txt['btn_player'], callback_data="menu_player"),
        InlineKeyboardButton(txt['btn_clan'], callback_data="menu_clan"),
        InlineKeyboardButton(txt['btn_calc'], callback_data="menu_calc"),
        InlineKeyboardButton(txt['btn_moe'], callback_data="menu_moe"),
        InlineKeyboardButton(txt['btn_news'], callback_data="menu_news"),
        InlineKeyboardButton(txt['btn_codes'], callback_data="menu_codes"),
        InlineKeyboardButton(txt['btn_maps'], callback_data="menu_maps") # <-- ADD THIS
    )
    markup.row(InlineKeyboardButton(txt['btn_modpack'], callback_data="menu_modpack"), 
               InlineKeyboardButton(txt['btn_settings'], callback_data="menu_settings"))

    bot.send_message(message.chat.id, txt['welcome'], reply_markup=markup, parse_mode="Markdown")


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

# --- Interactive Menu Callbacks ---
# --- Interactive Menu Callbacks ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_main_menu(call):
    chat_id = call.message.chat.id
    lang = get_user_language(chat_id)
    txt = STRINGS.get(lang, STRINGS['en'])
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
    # 5. MoE / MASTERY SUB-MENU
    elif call.data == "menu_moe":
        markup = InlineKeyboardMarkup(row_width=1)
        # These callbacks trigger 'handle_moe_category' in your script
        markup.add(
            InlineKeyboardButton("🏆 Mastery Values", callback_data="moe_cat_mastery"),
            InlineKeyboardButton("🎯 Gun Marks (MoE)", callback_data="moe_cat_gunmarks"),
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back")
        )
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="🎖️ *MoE & Mastery Requirements*\n\nSelect which statistics you would like to view for your tank:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    # 5. XP CALCULATOR HANDLER
    elif call.data == "menu_news":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ Subscribe", callback_data="news_sub_on"),
            InlineKeyboardButton("❌ Unsubscribe", callback_data="news_sub_off")
        )
        markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back"))
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="📰 *World of Tanks News*\n\nWould you like to receive automatic notifications when new articles are posted on the official website?",
            reply_markup=markup,
            parse_mode="Markdown"
        )

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
            "\n_Tip: Tap a code to copy it!_"
        )
        # Use edit_message_text so the menu updates in place
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_back"))
        bot.edit_message_text(response, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown", disable_web_page_preview=True)

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
@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def handle_set_language(call):
    lang_code = call.data.split('_')[1]
    set_user_language(call.from_user.id, lang_code)
    
    txt = STRINGS.get(lang_code, STRINGS['en'])
    bot.answer_callback_query(call.id, txt['lang_updated'])
    
    # Send user back to main menu automatically to see changes
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "dl_tg")
def handle_download(call):
    bot.answer_callback_query(call.id, "Sending...")
    bot.send_document(call.message.chat.id, SAVED_FILE_ID, caption="✅ Modpack Installer")
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
# --- Map Search Logic ---
def process_map_search(message):
    user_input = message.text.strip().lower()
    found_entry = None

    # Search logic: check every string in the "name" array
    for entry in MAPS_DATA:
        names_list = [n.lower() for n in entry.get("name", []) if n]
        if user_input in names_list:
            found_entry = entry
            break

    if found_entry:
        image_path = found_entry.get("root")
        
        # Check if the file actually exists on your server
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                bot.send_photo(
                    message.chat.id, 
                    photo, 
                    caption=f"🗺️ <b>Map Found:</b> {user_input.title()}",
                    parse_mode="HTML" # <-- Changed to HTML
                )
        else:
            bot.reply_to(
                message, 
                f"❌ I found the map, but the image file is missing at: <code>{image_path}</code>", 
                parse_mode="HTML" # <-- Changed to HTML
            )
    else:
        bot.reply_to(message, "❌ Map not found. Please check the spelling or try another name!")

@bot.message_handler(commands=["map", "maps"])
def handle_map_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "💡 Usage: `/map <map_name>` (e.g., `/map Himmelsdorf`)", parse_mode="Markdown")
        return
    message.text = parts[1]
    process_map_search(message)
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
# --- Settings Menu Handler ---
@bot.callback_query_handler(func=lambda call: call.data == "menu_settings")
def handle_settings(call):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
        InlineKeyboardButton("🇺🇦 Українська", callback_data="setlang_ua"),
        InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back")
    )
    
    bot.edit_message_text(
        "⚙️ *Settings*\n\nSelect your preferred language:", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=markup, 
        parse_mode='Markdown'
    )

# --- Language Selection Handler ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang_"))
def handle_set_language(call):
    lang_code = call.data.split("_")[1] # Extracts 'en', 'ru', or 'ua'
    user_id = call.from_user.id
    
    # Save to database
    set_user_language(user_id, lang_code)
    
    # Map codes to display names
    lang_names = {'en': 'English 🇬🇧', 'ru': 'Русский 🇷🇺', 'ua': 'Українська 🇺🇦'}
    selected_lang = lang_names.get(lang_code, "English 🇬🇧")
    
    # Quick popup notification
    bot.answer_callback_query(call.id, f"Language saved: {selected_lang}")
    
    # Update the message with a back button
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_back"))
    
    bot.edit_message_text(
        f"✅ Language successfully updated to **{selected_lang}**.\n\n"
        f"*(Note: You will need to add translations to your bot's text responses to see full changes.)*", 
        call.message.chat.id, 
        call.message.message_id, 
        reply_markup=markup, 
        parse_mode='Markdown'
    )
    
# --- MAIN EXECUTION ---
if __name__ == "__main__":
    logging.info("Starting combined application...")

    threading.Thread(target=check_news_loop, daemon=True).start()
    logging.info("RSS Checker Thread started.")

    threading.Thread(target=bot.infinity_polling, kwargs={'skip_pending': True}, daemon=True).start()
    logging.info("Telegram Bot Thread started.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)