import telebot
import json
import os
from telebot import util

# --- CONFIGURATION ---
API_TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
DATA_FILE = 'fixed_combined_db_with_images.json'

bot = telebot.TeleBot(API_TOKEN)

def load_tank_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def find_tank(search_name):
    tanks = load_tank_data()
    search_name = search_name.lower().strip()
    # Exact match
    for tank in tanks:
        if tank.get('name', '').lower() == search_name:
            return tank
    # Partial match
    for tank in tanks:
        if search_name in tank.get('name', '').lower():
            return tank
    return None

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    query = util.extract_arguments(message.text)
    if not query:
        bot.reply_to(message, "💡 *Usage:* `/stats tiger`", parse_mode="Markdown")
        return

    tank = find_tank(query)
    if not tank:
        bot.reply_to(message, f"❌ Tank *'{query}'* not found in the database.", parse_mode="Markdown")
        return

    # --- DATA LOADING ---
    name = tank.get('name', 'Unknown')
    nation = tank.get('nation', 'N/A').upper()
    tier = tank.get('tier', 'N/A')
    hp = tank.get('hp', 'N/A')

    # Effective Stats
    eff = tank.get('tanks_gg_effective_stats', {})
    fp = eff.get('firepower', {})
    mob = eff.get('mobility', {})
    
    # Chassis Stats (The section you just added)
    chassis = tank.get('chassis_stats', {})

    # Building the Message
    caption = (
        f"🛡️ *{name.upper()}* | Tier {tier} | {nation}\n"
        f"❤️ HP: `{hp}`\n\n"
        f"🔥 *FIREPOWER*\n"
        f"• DPM: `{fp.get('dpm', 0)}` | Reload: `{fp.get('reload_base', 'N/A')}s`\n"
        f"• Accuracy: `{fp.get('accuracy', 'N/A')}` | Aim: `{fp.get('aim_time', 'N/A')}s`\n\n"
        f"⚙️ *CHASSIS & MOBILITY*\n"
        f"• Move Dispersion: `{chassis.get('movement_dispersion', 'N/A')}`\n"
        f"• Rotate Dispersion: `{chassis.get('rotation_dispersion', 'N/A')}`\n"
        f"• Traverse Speed: `{chassis.get('traverse_speed', 'N/A')}°/s`\n"
        f"• Top Speed: `{mob.get('forward_speed', 'N/A')} km/h`"
        f"\n⚙️ *MOBILITY & CHASSIS*",
        f"• Top Speed: `{mob.get('forward_speed', 'N/A')} km/h`",
        f"• Hull Traverse: `{mob.get('hull_traverse', 'N/A')}°/s`",
        f"• Move Dispersion: `{chassis.get('movement_dispersion', 'N/A')}`",
    )

    # Image Logic
    images = tank.get('images')
    img_url = images.get('big_icon') if (images and isinstance(images, dict)) else None

    if img_url:
        try:
            bot.send_photo(message.chat.id, img_url, caption=caption, parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, caption, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, caption, parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot is running with Chassis Stats support...")
    bot.infinity_polling()