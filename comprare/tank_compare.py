import telebot
import json
import os

# ---------------- CONFIG ----------------
API_TOKEN = os.getenv("8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
FILE_NAME = "tanks_data.json"

bot = telebot.TeleBot(API_TOKEN)


# ---------------- LOAD TANKS ----------------
def load_tanks():
    if not os.path.exists(FILE_NAME):
        return []

    with open(FILE_NAME, "r") as f:
        return json.load(f)


# ---------------- FIND BEST MATCH ----------------
def get_best_match(search_name):
    tanks = load_tanks()
    search_name = search_name.lower()

    exact_match = None
    partial_match = None

    for tank in tanks:
        name = tank.get("name", "")
        if name.lower() == search_name:
            exact_match = tank
            break
        if search_name in name.lower() and not partial_match:
            partial_match = tank

    return exact_match or partial_match


# ---------------- CALCULATE STATS ----------------
def extract_stats(tank):
    stats = tank.get("tanks_gg_effective_stats", {})
    firepower = stats.get("firepower", {})
    mobility = stats.get("mobility", {})

    reload_time = float(firepower.get("reload_base") or 0)
    dmg = float(firepower.get("damage_avg") or 0)

    dpm = int((60 / reload_time) * dmg) if reload_time > 0 else 0

    return {
        "name": tank.get("name"),
        "nation": tank.get("nation", "unknown"),
        "tier": tank.get("tier", "?"),
        "hp": int(tank.get("hp", 0)),
        "dpm": dpm,
        "reload": reload_time,
        "speed": float(mobility.get("forward_speed") or 0),
        "accuracy": firepower.get("accuracy") or "N/A",
    }


# ---------------- COMMANDS ----------------

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(
        message,
        "👋 Send a tank name:\n"
        "`/tank Type59`\n\n"
        "Compare two tanks:\n"
        "`/compare Type59, WZ-111`",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["tank"])
def handle_tank(message):
    query = " ".join(message.text.split()[1:])

    if not query:
        bot.reply_to(message, "❌ Example: `/tank Type59`", parse_mode="Markdown")
        return

    tank = get_best_match(query)

    if not tank:
        bot.reply_to(message, "❌ Tank not found.")
        return

    s = extract_stats(tank)

    response = (
        f"🛡️ *{s['name']}* ({s['nation'].upper()})\n"
        f"Tier {s['tier']}\n\n"
        f"🔥 *Firepower*\n"
        f"• DPM: `{s['dpm']}`\n"
        f"• Reload: `{s['reload']}s`\n"
        f"• Accuracy: `{s['accuracy']}`\n\n"
        f"⚙️ *Mobility*\n"
        f"• Speed: `{s['speed']} km/h`\n\n"
        f"❤️ HP: `{s['hp']}`"
    )

    bot.send_message(message.chat.id, response, parse_mode="Markdown")


@bot.message_handler(commands=["compare"])
def handle_compare(message):
    parts = message.text.replace("/compare", "").split(",")

    if len(parts) < 2:
        bot.reply_to(message, "💡 Usage: `/compare Type59, WZ-111`", parse_mode="Markdown")
        return

    name1 = parts[0].strip()
    name2 = parts[1].strip()

    tank1 = get_best_match(name1)
    tank2 = get_best_match(name2)

    if not tank1 or not tank2:
        bot.reply_to(message, "❌ Could not find both tanks.")
        return

    s1 = extract_stats(tank1)
    s2 = extract_stats(tank2)

    def compare(v1, v2):
        if v1 > v2:
            return f"*{v1}* vs {v2}"
        elif v2 > v1:
            return f"{v1} vs *{v2}*"
        return f"{v1} vs {v2}"

    result = (
        f"⚔️ *Comparison*\n\n"
        f"1️⃣ {s1['name']}\n"
        f"2️⃣ {s2['name']}\n\n"
        f"🔥 DPM: {compare(s1['dpm'], s2['dpm'])}\n"
        f"❤️ HP: {compare(s1['hp'], s2['hp'])}\n"
        f"🚀 Speed: {compare(s1['speed'], s2['speed'])}"
    )

    bot.send_message(message.chat.id, result, parse_mode="Markdown")


# ---------------- START ----------------
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()