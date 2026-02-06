import sqlite3
import telebot
import requests
from telebot import types

# ================= CONFIG =================
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # <-- Put your bot token here
APP_ID = "02a11c34c34f9a3f73766e3646a1e21a"
REGION = "eu"
ADMINS = {1083670850}

bot = telebot.TeleBot(TOKEN)

# ================= WoT API LOGIC =================

def get_wot_stats(player_name):
    """Fetch stats and return them as a dictionary."""
    # 1. Get Account ID
    search_url = f"https://api.worldoftanks.{REGION}/wot/account/list/"
    search_params = {"application_id": APP_ID, "search": player_name}
    
    r = requests.get(search_url, params=search_params)
    data = r.json().get("data", [])
    
    if not data:
        raise Exception(f"Player '{player_name}' not found.")
    
    account_id = data[0]["account_id"]
    nickname = data[0]["nickname"]

    # 2. Get Player Info
    info_url = f"https://api.worldoftanks.{REGION}/wot/account/info/"
    info_params = {"application_id": APP_ID, "account_id": account_id}
    
    r = requests.get(info_url, params=info_params)
    player_data = r.json()["data"][str(account_id)]
    
    all_stats = player_data["statistics"]["all"]
    
    # 3. Format result
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

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome! Use /stats <player_name> to get WoT data.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "❌ Usage: /stats <player_name>")
            return

        player_name = args[1]
        bot.send_chat_action(message.chat.id, 'typing') # Show bot is "typing"
        
        stats = get_wot_stats(player_name)

        reply_text = (
            f"📊 **Stats for {stats['nickname']}**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🕹️ **Battles:** {stats['battles']}\n"
            f"🏆 **Wins:** {stats['wins']}\n"
            f"📈 **Winrate:** {stats['winrate']}%\n"
            f"💥 **Avg Damage:** {stats['avg_damage']}\n"
            f"💀 **Frags:** {stats['frags']}"
        )

        bot.reply_to(message, reply_text, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# ================= START BOT =================

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)