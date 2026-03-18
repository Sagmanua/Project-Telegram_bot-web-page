import telebot
import json
import os

# ---------------- CONFIG ----------------
# Use your environment variable or fallback to the provided token
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
FILE_NAME = "tanks_data.json"

bot = telebot.TeleBot(API_TOKEN)

# ---------------- LOAD TANKS ----------------
def load_tanks():
    if not os.path.exists(FILE_NAME):
        return []
    with open(FILE_NAME, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Skip the first element if it is just headers/metadata
        if data and data[0].get("tank_name") == "Tank Name":
            return data[1:]
        return data

# ---------------- FIND BEST MATCH ----------------
def get_best_match(search_name):
    tanks = load_tanks()
    search_name = search_name.lower()

    exact_match = None
    partial_match = None

    for tank in tanks:
        name = tank.get("tank_name", "")
        if name.lower() == search_name:
            exact_match = tank
            break
        if search_name in name.lower() and not partial_match:
            partial_match = tank

    return exact_match or partial_match

# ---------------- CALCULATE STATS ----------------
def extract_stats(tank):
    # Helper to clean strings like "9.50s", "31.7t", or "50 / 16"
    def clean_val(val, split_val=False):
        if not val or not isinstance(val, str):
            return 0.0
        # If it's a range like "50 / 16", take the first number (top speed)
        if split_val and "/" in val:
            val = val.split("/")[0]
        
        # Remove units like 's', 't', '°/s', etc.
        clean_str = "".join(c for c in val if c.isdigit() or c == '.')
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    return {
        "name": tank.get("full_name", "Unknown"),
        "dpm": clean_val(tank.get("Tank DPM")),
        "reload": clean_val(tank.get("Reload")),
        "accuracy": clean_val(tank.get("Acc")),
        "speed": clean_val(tank.get("Speed"), split_val=True),
        "hp": clean_val(tank.get("Health"))
    }

# ---------------- BOT HANDLERS ----------------
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(message, "📊 *Tank Compare Bot*\n\n"
                          "Usage:\n"
                          "• `/info T-34` - Get specific tank stats\n"
                          "• `/compare T-34, IS-M` - Compare two tanks", 
                          parse_mode="Markdown")

@bot.message_handler(commands=["info"])
def handle_info(message):
    name = message.text.replace("/info", "").strip()
    tank = get_best_match(name)

    if not tank:
        bot.reply_to(message, "❌ Tank not found.")
        return

    s = extract_stats(tank)
    response = (
        f"🛡️ *{s['name']}* (Tier {tank.get('tier', 'N/A')})\n\n"
        f"🔥 *Firepower*\n"
        f"• DPM: `{s['dpm']}`\n"
        f"• Reload: `{s['reload']}s`\n"
        f"• Accuracy: `{s['accuracy']}`\n\n"
        f"⚙️ *Mobility*\n"
        f"• Top Speed: `{s['speed']} km/h`\n\n"
        f"❤️ HP: `{s['hp']}`"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(commands=["compare"])
def handle_compare(message):
    parts = message.text.replace("/compare", "").split(",")

    if len(parts) < 2:
        bot.reply_to(message, "💡 Usage: `/compare T-34, IS-M`", parse_mode="Markdown")
        return

    tank1 = get_best_match(parts[0].strip())
    tank2 = get_best_match(parts[1].strip())

    if not tank1 or not tank2:
        bot.reply_to(message, "❌ Could not find both tanks.")
        return

    s1 = extract_stats(tank1)
    s2 = extract_stats(tank2)

    def compare_vals(v1, v2, lower_is_better=False):
        if v1 == v2: return f"{v1} vs {v2}"
        if lower_is_better:
            return f"*{v1}* vs {v2}" if v1 < v2 else f"{v1} vs *{v2}*"
        return f"*{v1}* vs {v2}" if v1 > v2 else f"{v1} vs *{v2}*"

    response = (
        f"🆚 *{s1['name']}* vs *{s2['name']}*\n\n"
        f"🔥 DPM: {compare_vals(s1['dpm'], s2['dpm'])}\n"
        f"⏱️ Reload: {compare_vals(s1['reload'], s2['reload'], True)}\n"
        f"🎯 Accuracy: {compare_vals(s1['accuracy'], s2['accuracy'], True)}\n"
        f"⚡ Speed: {compare_vals(s1['speed'], s2['speed'])}\n"
        f"❤️ HP: {compare_vals(s1['hp'], s2['hp'])}"
    )
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()