import sqlite3
import telebot
import os
import json
import io
from PIL import Image
from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

# Prioritize .env token, then fallback to hardcoded from app1.py
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
DATABASE = "chat_clan.db"
DATA_FILE = "tanks_data.json"

bot = telebot.TeleBot(TOKEN)

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

# --- Tank Data Logic ---
def load_tanks():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data and isinstance(data, list) and data[0].get("tank_name") == "Tank Name":
                return data[1:]
            return data
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []

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
                # Support both relative and absolute paths from the json
                full_path = p if p.startswith('images') else f"images_equipment/{p}"
                if os.path.exists(full_path):
                    valid_images.append(Image.open(full_path))
            
            if valid_images:
                grid_images.append(valid_images)
                max_cols = max(max_cols, len(valid_images))

        if not grid_images:
            return None

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

# --- Math Functions ---
def calculate_xp(skill_number, current_percentage):
    if skill_number < 1: return 0
    base_xp_first_skill = 210064
    xp_previous_skills = base_xp_first_skill * (2**(skill_number - 1) - 1)
    xp_current_skill = base_xp_first_skill * (2**(skill_number - 1)) * (pow(2, current_percentage / 100) - 1)
    return round(xp_previous_skills + xp_current_skill)



# --- Bot Handlers ---


@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    welcome_text = (
        "Tank Assistant Online!\n\n"
        "📜 *Commands:*\n"
        "• `/info <tank>` - Get stats\n"
        "• `/compare <tank1>, <tank2>` - Compare two tanks\n"
        "• `/equipment <tank>` - Best setup images\n"
        "• `/crew <tank>` - Crew skill images\n"
        "• `/clan <name>` - Join a clan group\n"
        "• `/masagge <text>` - Message your clan\n"
        "• `/exp <skill_num> <%>` - Calculate XP needed"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=["info"])
def handle_info(message):
    name = message.text.replace("/info", "").strip()
    tank = get_best_match(name)
    if not tank:
        bot.reply_to(message, "❌ Tank not found.")
        return

    s = extract_stats(tank)
    response = (
        f"🛡️ *{s['full_name']}* (Tier {s['tier']})\n\n"
        f"🔥 *Firepower*\n"
        f"• DPM: `{s['dpm']}`\n"
        f"• Damage: `{s['dmg']}`\n"
        f"• Reload: `{s['reload']}`\n"
        f"• Pen: `{s['pen']}`\n"
        f"• Velocity: `{s['velo']} m/s`\n"
        f"• Acc: `{s['acc']}` | Aim: `{s['aim']}`\n"
        f"• Dispersion: `{s['dispersion']}`\n"
        f"• Dep/Elev: `{s['elevation']}`\n\n"
        f"⚙️ *Mobility & Protection*\n"
        f"• Speed: `{s['speed']} km/h`\n"
        f"• Traverse: `{s['traverse']}`\n"
        f"• Power: `{s['power']} hp` ({s['pw']} hp/t)\n"
        f"• Weight: `{s['weight']}`\n"
        f"• HP: `{s['hp']}` | VR: `{s['vr']}m`"
    )
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
        if member_id != message.chat.id:
            try:
                bot.send_message(member_id, f"📢 **Clan Message:**\n{text_to_send}", parse_mode="Markdown")
                count += 1
            except: continue
    bot.reply_to(message, f"Message sent to {count} clan members!")

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
        skill_num = int(parts[1])
        percentage = int(parts[2])
        total_needed = calculate_xp(skill_num, percentage)
        bot.send_message(message.chat.id, f"Total XP needed for skill {skill_num} at {percentage}%: **{total_needed:,}**", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "Please use numbers: `/exp 2 50`")

if __name__ == "__main__":
    setup_database()
    print("Bot started...")
    bot.infinity_polling()