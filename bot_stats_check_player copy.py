import telebot
import requests

# ================= CONFIG =================
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
APP_ID = "02a11c34c34f9a3f73766e3646a1e21a"
REGION = "eu"

bot = telebot.TeleBot(TOKEN)

# ================= WoT API LOGIC =================

def get_clan_id(clan_name):
    url = f"https://api.worldoftanks.{REGION}/wot/clans/list/"
    params = {
        "application_id": APP_ID,
        "search": clan_name,
        "limit": 1
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json().get("data", [])
    if not data:
        return None
    return data[0]["clan_id"]

def get_clan_stats(clan_id):
    url = f"https://api.worldoftanks.{REGION}/wot/clans/info/"
    params = {
        "application_id": APP_ID,
        "clan_id": clan_id,
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()["data"][str(clan_id)]

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Welcome! Use `/clan <tag>` to get WoT Clan data.", parse_mode="Markdown")

@bot.message_handler(commands=['clan'])
def clan_command(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: /clan <clan_tag_or_name>")
            return

        search_query = args[1]
        bot.send_chat_action(message.chat.id, 'typing')

        # 1. Resolve Name to ID
        clan_id = get_clan_id(search_query)
        if not clan_id:
            bot.reply_to(message, f"❌ Clan '{search_query}' not found.")
            return

        # 2. Get Stats
        stats = get_clan_stats(clan_id)

        # 3. Format Response
        reply_text = (
            f"🛡️ **Clan:** {stats['name']} [{stats['tag']}]\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👥 **Members:** {stats['members_count']}\n"
            f"⭐ **Motto:** {stats['motto']}\n"
            f"📝 **Description:** {stats['description'][:100]}..." # Truncated for brevity
        )

        bot.reply_to(message, reply_text, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)