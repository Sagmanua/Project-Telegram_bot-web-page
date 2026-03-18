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
        'welcome': "👋 *Welcome to Tank Assistant!\nI can help you find tank stats, check player progress, manage your clan, download mods, and find the latest rewards.\n👇 Select an option below to get started:*",
        'btn_tank': "🛡️ Tank Info", 'btn_compare': "🆚 Compare", 'btn_player': "📊 Player Stats",
        'btn_clan': "🏰 Clan Tools", 'btn_calc': "🧮 XP Calc", 'btn_moe': "🎖️ MoE/Mastery",
        'btn_news': "📰 News", 'btn_codes': "🎁 Codes", 'btn_modpack': "📦 Modpack",
        'btn_maps': "🗺️ Maps", 'btn_settings': "⚙️ Settings",
        'choose_lang': "⚙️ *Settings*\n\nSelect your preferred language:", 'lang_updated': "✅ Language updated to English 🇬🇧"
    },
    'ru': {
        'welcome': "👋 *Добро пожаловать в Tank Assistant!*",
        'btn_tank': "🛡️ Инфо Танка", 'btn_compare': "🆚 Сравнение", 'btn_player': "📊 Статистика",
        'btn_clan': "🏰 Клан", 'btn_calc': "🧮 Калькулятор XP", 'btn_moe': "🎖️ Отметки/Мастер",
        'btn_news': "📰 Новости", 'btn_codes': "🎁 Бонус Коды", 'btn_modpack': "📦 Модпак",
        'btn_maps': "🗺️ Карты", 'btn_settings': "⚙️ Настройки",
        'choose_lang': "⚙️ *Настройки*\n\nВыберите язык:", 'lang_updated': "✅ Язык изменен на Русский 🇷🇺"
    },
    'ua': {
        'welcome': "👋 *Ласкаво просимо до Tank Assistant!*",
        'btn_tank': "🛡️ Інфо Танка", 'btn_compare': "🆚 Порівняння", 'btn_player': "📊 Статистика",
        'btn_clan': "🏰 Клан", 'btn_calc': "🧮 Калькулятор XP", 'btn_moe': "🎖️ Відмітки/Майстер",
        'btn_news': "📰 Новини", 'btn_codes': "🎁 Бонус Коди", 'btn_modpack': "📦 Модпак",
        'btn_maps': "🗺️ Карти", 'btn_settings': "⚙️ Налаштування",
        'choose_lang': "⚙️ *Налаштування*\n\nОберіть мову:", 'lang_updated': "✅ Мову змінено на Українську 🇺🇦"
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

def escape_markdown(text):
    for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
        text = text.replace(char, f'\\{char}')
    return text

def extract_stats(tank):
    def clean_val(val, take_first=False):
        if not val or not isinstance(val, (str, int, float)): return 0.0
        val = str(val)
        if take_first and "/" in val: val = val.split("/")[0]
        try: return float("".join(c for c in val if c.isdigit() or c == '.'))
        except ValueError: return 0.0

    return {
        "full_name": tank.get("full_name", "Unknown"), "tier": tank.get("tier", "N/A"),
        "dpm": tank.get("Tank DPM", "0"), "dmg": tank.get("Dmg", "0"), "reload": tank.get("Reload", "0s"),
        "pen": tank.get("Pen", "0"), "velo": tank.get("Velo", "0"), "acc": tank.get("Acc", "0"),
        "aim": tank.get("Aim", "0s"), "dispersion": tank.get("Dispresion", "0"),
        "elevation": tank.get("DeP/Elev", "0"), "speed": tank.get("Speed", "0"),
        "traverse": tank.get("Traverse", "0"), "power": tank.get("Power", "0"),
        "pw": tank.get("P/W", "0"), "weight": tank.get("Weight", "0"),
        "hp": tank.get("Health", "0"), "vr": tank.get("VR", "0"),
        "n_dpm": clean_val(tank.get("Tank DPM")), "n_dmg": clean_val(tank.get("Dmg")),
        "n_reload": clean_val(tank.get("Reload")), "n_pen": clean_val(tank.get("Pen")),
        "n_velo": clean_val(tank.get("Velo")), "n_acc": clean_val(tank.get("Acc")),
        "n_aim": clean_val(tank.get("Aim")), "n_speed": clean_val(tank.get("Speed"), True),
        "n_traverse": clean_val(tank.get("Traverse")), "n_power": clean_val(tank.get("Power")),
        "n_pw": clean_val(tank.get("P/W")), "n_hp": clean_val(tank.get("Health")), "n_vr": clean_val(tank.get("VR"))
    }

def process_and_combine_images(image_paths_list):
    try:
        grid_images = []
        max_cols = 0
        for row in image_paths_list:
            valid_images = [Image.open(p if p.startswith('images') else f"images_equipment/{p}") for p in row if os.path.exists(p if p.startswith('images') else f"images_equipment/{p}")]
            if valid_images:
                grid_images.append(valid_images)
                max_cols = max(max_cols, len(valid_images))
        if not grid_images: return None

        img_w, img_h = grid_images[0][0].size
        combined_img = Image.new('RGBA', (max_cols * img_w, len(grid_images) * img_h), (0, 0, 0, 0))
        for row_idx, row_imgs in enumerate(grid_images):
            for col_idx, img in enumerate(row_imgs): combined_img.paste(img, (col_idx * img_w, row_idx * img_h))

        img_byte_arr = io.BytesIO()
        combined_img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr
    except Exception as e: print(f"Image Error: {e}"); return None

# --- Next Step Logic ---
def process_tank_info(message):
    tank = get_best_match(message.text.strip())
    if not tank: return bot.reply_to(message, "❌ Tank not found.")
    s, tank_id = extract_stats(tank), tank.get("tank_id")
    image_url = get_tank_image_by_id(tank_id) if tank_id else None

    markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton("⚙️ Equipment", callback_data=f"visual_equipment_{tank['full_name']}"),
        InlineKeyboardButton("👨‍✈️ Crew Skills", callback_data=f"visual_crew_{tank['full_name']}")
    )

    response = (f"🛡️ *{s['full_name']}* (Tier {s['tier']})\n\n🔥 DPM: `{s['dpm']}`\n💥 Dmg: `{s['dmg']}`\n⏱️ Reload: `{s['reload']}`\n🎯 Pen: `{s['pen']}`\n🚀 Velo: `{s['velo']} m/s`\n🔬 Acc: `{s['acc']}`\n⏲️ Aim: `{s['aim']}`\n🌀 Disp: `{s['dispersion']}`\n📐 Elev: `{s['elevation']}`\n⚡ Speed: `{s['speed']} km/h`\n🔄 Trav: `{s['traverse']}`\n🐎 Power: `{s['power']}`\n⚖️ P/W: `{s['pw']}`\n🏋️ Wgt: `{s['weight']}`\n❤️ HP: `{s['hp']}`\n👁️ VR: `{s['vr']}m`")
    bot.send_photo(message.chat.id, image_url, caption=response, parse_mode="Markdown", reply_markup=markup) if image_url else bot.send_message(message.chat.id, response, parse_mode="Markdown", reply_markup=markup)

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
    base = 210064
    return round(base * (2**(skill_number - 1) - 1) + base * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1))

def get_clan_id_by_tag(tag):
    try:
        resp = requests.get(f"https://api.worldoftanks.{REGION}/wot/clans/list/?application_id={WG_APP_ID}&search={tag}").json()
        if resp['status'] == 'ok' and resp['data']: return next((c['clan_id'] for c in resp['data'] if c['tag'].upper() == tag.upper()), None)
    except Exception as e: print(f"WG search error: {e}")
    return None

def get_active_members(clan_tag):
    clan_id = get_clan_id_by_tag(clan_tag)
    if not clan_id: return f"❌ <b>Clan [{clan_tag.upper()}] not found.</b>"
    
    clan_data = requests.get(f"https://api.worldoftanks.{REGION}/wot/clans/info/?application_id={WG_APP_ID}&clan_id={clan_id}").json()
    if clan_data['status'] != 'ok': return "❌ WG API Error."

    account_ids = ",".join([str(m['account_id']) for m in clan_data['data'][str(clan_id)]['members']])
    status_data = requests.get(f"https://api.worldoftanks.{REGION}/wot/account/info/?application_id={WG_APP_ID}&account_id={account_ids}&fields=nickname,last_battle_time").json()

    active_list = []
    current_time = time.time()
    if status_data['status'] == 'ok':
        for acc_id, info in status_data['data'].items():
            if info and info.get('last_battle_time') and (current_time - info['last_battle_time']) < 7200:
                active_list.append(f"• <b>{info['nickname']}</b> ({int((current_time - info['last_battle_time']) // 60)}m ago)")

    return f"🔥 <b>Recently Active in [{clan_tag.upper()}]:</b>\n\n" + "\n".join(active_list) if active_list else f"No players from <b>[{clan_tag.upper()}]</b> active in last 2 hours."

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
        try:
            feed = feedparser.parse(RSS_URL)
            if feed.entries:
                latest = feed.entries[0]
                saved_link = get_last_link()
                if latest.link != saved_link:
                    if saved_link is not None:
                        msg = f"🆕 *New WoT News!*\n\n*{escape_markdown(latest.title)}*\n{latest.link}"
                        for user_id in get_subscribers():
                            try: bot.send_message(user_id, msg, parse_mode="Markdown")
                            except: pass
                    set_last_link(latest.link)
        except Exception as e: print(f"RSS ERROR: {e}")
        time.sleep(300)

# --- Bot Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    txt = STRINGS.get(get_user_language(message.chat.id), STRINGS['en'])
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton(txt['btn_tank'], callback_data="menu_tank"), InlineKeyboardButton(txt['btn_compare'], callback_data="menu_compare"),
        InlineKeyboardButton(txt['btn_player'], callback_data="menu_player"), InlineKeyboardButton(txt['btn_clan'], callback_data="menu_clan"),
        InlineKeyboardButton(txt['btn_calc'], callback_data="menu_calc"), InlineKeyboardButton(txt['btn_moe'], callback_data="menu_moe"),
        InlineKeyboardButton(txt['btn_news'], callback_data="menu_news"), InlineKeyboardButton(txt['btn_codes'], callback_data="menu_codes"),
        InlineKeyboardButton(txt['btn_maps'], callback_data="menu_maps")
    ).row(InlineKeyboardButton(txt['btn_modpack'], callback_data="menu_modpack"), InlineKeyboardButton(txt['btn_settings'], callback_data="menu_settings"))
    bot.send_message(message.chat.id, txt['welcome'], reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_main_menu(call):
    chat_id, txt = call.message.chat.id, STRINGS.get(get_user_language(call.message.chat.id), STRINGS['en'])
    if call.data == "menu_settings":
        markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en"), InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"), InlineKeyboardButton("🇺🇦 Українська", callback_data="setlang_ua"), InlineKeyboardButton("⬅️ Back", callback_data="menu_back"))
        bot.edit_message_text(txt['choose_lang'], chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    elif call.data == "menu_tank": bot.send_message(chat_id, "🛡️ Enter tank name:")
    elif call.data == "menu_modpack":
        markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("📥 Telegram", callback_data="dl_tg"), InlineKeyboardButton("🌐 Website", url=WEBSITE_URL), InlineKeyboardButton("⬅️ Back", callback_data="menu_back"))
        bot.edit_message_text("📦 *Modpack*", chat_id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    elif call.data == "menu_maps":
        bot.register_next_step_handler(bot.send_message(chat_id, "🗺️ Enter the map name (e.g., Prokhorovka):"), process_map_search)
    elif call.data == "menu_back":
        bot.delete_message(chat_id, call.message.message_id)
        start(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "dl_tg")
def handle_download(call):
    bot.answer_callback_query(call.id, "Sending...")
    try: bot.send_document(call.message.chat.id, SAVED_FILE_ID, caption="✅ Modpack Installer")
    except Exception as e: bot.send_message(call.message.chat.id, f"❌ Failed to send: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def handle_set_language(call):
    lang_code = call.data.split('_')[1]
    set_user_language(call.from_user.id, lang_code)
    bot.answer_callback_query(call.id, STRINGS.get(lang_code, STRINGS['en'])['lang_updated'])
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('visual_'))
def handle_tank_visuals(call):
    parts = call.data.split('_')
    tank_info = get_best_match(parts[2])
    if not tank_info: return bot.answer_callback_query(call.id, "❌ Tank data lost.")
    
    bot.answer_callback_query(call.id, f"Generating {parts[1]}...")
    img = process_and_combine_images([tank_info.get('equipment', [])] if parts[1] == 'equipment' else [tank_info.get('crew', {}).get(r) for r in ['comander', 'driver', 'gunner', 'loader', 'radist'] if r in tank_info.get('crew', {})])
    
    if img: bot.send_photo(call.message.chat.id, img, caption=f"✅ {parts[1].capitalize()} setup for *{tank_info.get('full_name')}*", parse_mode="Markdown")
    else: bot.send_message(call.message.chat.id, f"⚠️ Could not generate {parts[1]} image. Check server assets.")

# Add additional command handlers similarly... (truncated for brevity, ensure you copy over any other specific ones like `/player_stats` you need directly from your original code)

@bot.message_handler(commands=['player_stats'])
def stats_command(message):
    try:
        if len(message.text.split()) < 2: return bot.reply_to(message, "❌ Usage: /player_stats <player_name>")
        bot.send_chat_action(message.chat.id, 'typing') 
        stats = get_wot_stats(message.text.split()[1])
        save_player_stats(stats)
        bot.reply_to(message, f"📊 **Stats for {stats['nickname'].replace('_', '\\_')}**\n━━━━━━━━━━━━━━━\n🕹️ **Battles:** `{stats['battles']}`\n🏆 **Wins:** `{stats['wins']}`\n📈 **Winrate:** `{stats['winrate']}%`\n💥 **Avg Damage:** `{stats['avg_damage']}`\n💀 **Frags:** `{stats['frags']}`", parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"⚠️ Error: {escape_markdown(str(e))}", parse_mode="Markdown")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    logging.info("Starting combined application...")

    # Start the RSS loop in a background daemon thread
    threading.Thread(target=check_news_loop, daemon=True).start()
    logging.info("RSS Checker Thread started.")

    # Start the Telegram Bot in a background daemon thread
    threading.Thread(target=bot.infinity_polling, kwargs={'skip_pending': True}, daemon=True).start()
    logging.info("Telegram Bot Thread started.")

    # Start the Flask Application on the main thread
    # IMPORTANT: debug=False is required here. If it is True, the Flask auto-reloader 
    # will spawn a second process and cause duplicate threads, breaking your bot token.
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)