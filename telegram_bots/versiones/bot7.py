import sqlite3
import telebot
import os
import json
import io
from PIL import Image
import requests
import time

from dotenv import load_dotenv

# --- Configuration & Setup ---
load_dotenv()

# Prioritize .env token, then fallback to hardcoded from app1.py
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
WG_APP_ID = os.getenv("WG_APP_ID") or "1c67a69b2758f598f6edab23ca7dbb7c"
REGION = "eu"

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
# --- Tank Data Logic ---
def load_tanks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if data and isinstance(data, list) and data[0].get("tank_name") == "Tank Name":
            return data[1:]
        return data


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
    params = {
        "application_id": WG_APP_ID,
        "tank_id": tank_id
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if data["status"] == "ok":
            tank_data = data["data"].get(str(tank_id))
            if tank_data:
                # choose one:
                # small_icon
                # contour_icon (transparent, cleaner)
                # big_icon
                return tank_data["images"]["big_icon"]

    except Exception as e:
        print("WG Image Error:", e)

    return None
def escape_md(text):
    """Escapes characters for Markdown parse_mode."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
def escape_markdown(text):
    """Escapes characters that interfere with Telegram Markdown formatting."""
    # List of characters that need to be escaped for Markdown mode
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

def get_wot_stats(player_name):
    """Fetch stats and return them as a dictionary."""
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
        "• `/messagge <text>` - Message your clan\n"
        "• `/exp <skill_num> <%>` - Calculate XP needed\n"
        "• `/clan_online <name_of_clan> ` - Calculate XP neede\n"
        "• `/player_stats <name_of_player> - you can see statistic of player`\n"
        "• `/progress <name_of_player> <day>- you can see statistic of player in some period but before see you need to use /player_stats to start take datos`"
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

    # 🔥 GET IMAGE USING TANK_ID
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
        bot.send_photo(
            message.chat.id,
            image_url,
            caption=response,
            parse_mode="Markdown"
        )
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

@bot.message_handler(commands=['messagge'])
def send_clan_message(message):

    if not message.reply_to_message:
        bot.reply_to(message, "Reply to a message with /messagge")
        return

    members = get_clan_members(message.from_user.id)

    if not members:
        bot.reply_to(message, "You aren't in a clan yet! Use /clan first.")
        return

    count = 0
    original = message.reply_to_message

    for member_id in members:
        if member_id != message.from_user.id:
            try:
                bot.copy_message(
                    chat_id=member_id,
                    from_chat_id=original.chat.id,
                    message_id=original.message_id
                )
                count += 1
            except Exception as e:
                print(e)
                continue

    bot.reply_to(message, f"✅ Message sent to {count} clan members!")

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

        error_msg = str(e).replace("_", "\\_")
        bot.reply_to(message, f"⚠️ Error: {error_msg}", parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")



@bot.message_handler(commands=['progress'])
def progress_command(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "❌ Usage: /progress <player_name> <days>")
            return

        player_name = args[1]
        days = int(args[2])

        # 1. Get current live stats
        current = get_wot_stats(player_name)
        # 2. Get historical stats from DB
        old = get_stats_from_days_ago(current["nickname"], days)

        if not old:
            bot.reply_to(message, f"❓ No data found for {escape_markdown(player_name)} from {days} days ago.")
            return

        # Unpack: old_damage is total damage stored in DB
        old_battles, old_wins, old_damage, old_frags, old_date = old

        # Calculate Differences (The "Session")
        diff_battles = current["battles"] - old_battles
        diff_wins = current["wins"] - old_wins
        diff_damage = (current["avg_damage"] * current["battles"]) - old_damage
        diff_frags = current["frags"] - old_frags

        # Calculate Session Performance
        if diff_battles > 0:
            session_winrate = round((diff_wins / diff_battles) * 100, 2)
            session_avg_dmg = round(diff_damage / diff_battles)
        else:
            session_winrate = 0
            session_avg_dmg = 0

        # Sanitize all dynamic data before adding it to the markdown string
        safe_name = escape_markdown(current['nickname'])
        safe_date = escape_markdown(str(old_date))

        # Format the response
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
        # Sanitize error messages too, in case they contain underscores
        bot.reply_to(message, f"⚠️ Error: {escape_markdown(str(e))}")
if __name__ == "__main__":
    setup_database()
    print("Bot started...")
    bot.infinity_polling()