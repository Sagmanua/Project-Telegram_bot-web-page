import sqlite3
import telebot
import requests
from telebot import types

# ================= CONFIG =================
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  
APP_ID = ""
REGION = "eu"
ADMINS = {1083670850}

bot = telebot.TeleBot(TOKEN)

# ================= WoT API LOGIC =================

def get_wot_stats(player_name):
    """Fetch stats and return them as a dictionary."""
    search_url = f"https://api.worldoftanks.{REGION}/wot/account/list/"
    search_params = {"application_id": APP_ID, "search": player_name}
    
    r = requests.get(search_url, params=search_params)
    data = r.json().get("data", [])
    
    if not data:
        raise Exception(f"Player '{player_name}' not found.")
    
    account_id = data[0]["account_id"]
    nickname = data[0]["nickname"]

    info_url = f"https://api.worldoftanks.{REGION}/wot/account/info/"
    info_params = {"application_id": APP_ID, "account_id": account_id}
    
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
        bot.send_chat_action(message.chat.id, 'typing') 
        
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