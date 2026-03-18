import sqlite3
import telebot
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
DATABASE = "chat_clan.db"

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
        # Ensure user exists first
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("UPDATE users SET clan_name=? WHERE user_id=?", (clan_name, user_id))

def get_clan_members(user_id):
    """Returns a list of all user_ids in the same clan as the given user."""
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        # 1. Find which clan the sender belongs to
        cur.execute("SELECT clan_name FROM users WHERE user_id = ?", (user_id,))
        result = cur.fetchone()

        if not result or not result[0]:
            return [] 

        clan_name = result[0]

        # 2. Find all members of that clan
        cur.execute("SELECT user_id FROM users WHERE clan_name = ?", (clan_name,))
        return [row[0] for row in cur.fetchall()]

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.reply_to(message, "Welcome! Use /clan <name> to join a group.")

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
    # Split the command from the text
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
        # Don't send the message back to the sender
        if member_id != message.chat.id:
            try:
                bot.send_message(member_id, f"📢 **Clan Message:**\n{text_to_send}", parse_mode="Markdown")
                count += 1
            except Exception as e:
                print(f"Could not send to {member_id}: {e}")

    bot.reply_to(message, f"Message sent to {count} clan members!")

if __name__ == "__main__":
    setup_database()
    print("Bot is online...")
    bot.polling()