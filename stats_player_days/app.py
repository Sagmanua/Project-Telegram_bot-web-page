import sqlite3
import telebot
import os
import json
import io
from PIL import Image
import requests
import time

from dotenv import load_dotenv
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"


bot = telebot.TeleBot(TOKEN)

# --- Configuration & Setup ---
load_dotenv()

def setup_database():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        # USERS TABLE (existing)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            clan_name TEXT,
            lang TEXT DEFAULT 'en'
        )
        """)

        # PLAYER STATISTICS TABLE (NEW)
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
def save_player_stats(stats):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO player_statistics 
        (nickname, battles, wins, damage, frags)
        VALUES (?, ?, ?, ?, ?)
        """, (
            stats["nickname"],
            stats["battles"],
            stats["wins"],
            stats["avg_damage"] * stats["battles"],  # total damage
            stats["frags"]
        ))

# Prioritize .env token, then fallback to hardcoded from app1.py
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
WG_APP_ID = os.getenv("WG_APP_ID") or "1c67a69b2758f598f6edab23ca7dbb7c"
REGION = "eu"

DATABASE = "chat_clan.db"
DATA_FILE = "tanks_data.json"
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
            bot.reply_to(message, f"❓ No data found for {player_name} from {days} days ago.")
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

        # Format the response
        reply = (
            f"📈 **Progress for {current['nickname']}**\n"
            f"🗓️ *Last {days} days (since {old_date})*\n"
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
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

if __name__ == "__main__":
    setup_database()
    print("Bot started...")
    bot.infinity_polling()