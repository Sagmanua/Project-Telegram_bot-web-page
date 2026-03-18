import telebot
import requests
import json
import os

# --- CONFIGURATION ---
API_TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
APP_ID = '02a11c34c34f9a3f73766e3646a1e21a'
FILE_NAME = 'tanks_cache.json'

bot = telebot.TeleBot(API_TOKEN)

# ------------------ SYNC TANK LIST ------------------
def sync_tanks():
    url = "https://api.worldoftanks.eu/wot/encyclopedia/vehicles/"
    params = {'application_id': APP_ID, 'fields': 'tank_id,name'}
    response = requests.get(url, params=params).json()

    if response.get('status') == 'ok':
        with open(FILE_NAME, 'w') as f:
            json.dump(response['data'], f)
        return True
    return False

# ------------------ FIND BEST MATCH ------------------
def get_best_match(search_name):
    if not os.path.exists(FILE_NAME):
        sync_tanks()

    with open(FILE_NAME, 'r') as f:
        tanks = json.load(f)

    search_name = search_name.lower()
    matches = []

    for tid, info in tanks.items():
        tank_name = info['name']
        if tank_name.lower() == search_name:
            return tid, tank_name
        if search_name in tank_name.lower():
            matches.append((tid, tank_name))

    return matches[0] if matches else (None, None)

# ------------------ GET FULL STATS ------------------
def get_stats(tank_id):
    url = "https://api.worldoftanks.eu/wot/encyclopedia/vehicles/"
    params = {'application_id': APP_ID, 'tank_id': tank_id}
    res = requests.get(url, params=params).json()
    return res['data'][str(tank_id)] if res.get('status') == 'ok' else None

# ------------------ TELEGRAM HANDLERS ------------------

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Send me a tank name (e.g., `/tank Maus`) to see its stats and image.", parse_mode='Markdown')

@bot.message_handler(commands=['tank'])
def handle_tank_request(message):
    query = ' '.join(message.text.split()[1:])
    
    if not query:
        bot.reply_to(message, "Please provide a tank name. Example: `/tank IS-7`", parse_mode='Markdown')
        return

    bot.send_chat_action(message.chat.id, 'upload_photo')
    
    tid, full_name = get_best_match(query)

    if not tid:
        bot.reply_to(message, "❌ Tank not found.")
        return

    stats = get_stats(tid)
    if not stats:
        bot.reply_to(message, "❌ Failed to fetch data from Wargaming.")
        return

    # Data Parsing
    dp = stats.get('default_profile', {})
    armor = dp.get('armor', {})
    gun = dp.get('gun', {})
    engine = dp.get('engine', {})
    turret = dp.get('turret', {})
    h = armor.get('hull', {})
    t = armor.get('turret', {})
    
    # Image URL
    image_url = stats.get('images', {}).get('big_icon')

    # Math for DPM and P/W
    reload_time = gun.get('reload_time')
    ammo = dp.get('ammo', [])
    avg_damage = ammo[0].get('damage', [0, 0])[1] if ammo else 0
    dpm = round((60 / reload_time) * avg_damage) if reload_time else "N/A"
    
    weight = dp.get('weight', 0)
    power = engine.get('power', 0)
    p_to_w = round(power / (weight / 1000), 2) if weight else "N/A"

    # Formatting the Response
    premium_tag = "🌟 *PREMIUM*" if stats.get('is_premium') else ""
    
    caption = (
        f"🛡️ *{full_name.upper()}* ({stats.get('nation').upper()})\n"
        f"Tier {stats.get('tier')} {stats.get('type').replace('_', ' ').title()} {premium_tag}\n\n"
        f"🔥 *FIREPOWER*\n"
        f"• DPM: `{dpm}` | Reload: `{reload_time}s`\n"
        f"• Gun: {gun.get('name')}\n\n"
        f"⚙️ *MOBILITY*\n"
        f"• Speed: `{dp.get('speed_forward')}/{dp.get('speed_backward')} km/h`\n"
        f"• P/W: `{p_to_w} hp/t`\n\n"
        f"📊 *ARMOR*\n"
        f"• Hull: `{h.get('front')}/{h.get('sides')}/{h.get('rear')}`\n"
        f"• View Range: `{turret.get('view_range')}m`"
    )

    if image_url:
        bot.send_photo(message.chat.id, image_url, caption=caption, parse_mode='Markdown')
    else:
        bot.reply_to(message, caption, parse_mode='Markdown')

# ------------------ START BOT ------------------
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()