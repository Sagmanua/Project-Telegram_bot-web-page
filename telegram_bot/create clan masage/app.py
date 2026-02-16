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
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        cur.execute("UPDATE users SET clan_name=? WHERE user_id=?", (clan_name, user_id))

def get_clan(user_id):
        with sqlite3.connect(DATABASE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT clan_name FROM users WHERE user_id = ?", (user_id,))
            result = cur.fetchone()

            if not result or not result[0]:
                return [] 

            clan_name = result[0]

            cur.execute("SELECT user_id FROM users WHERE clan_name = ?", (clan_name,))
            return [row[0] for row in cur.fetchall()]
def masagge_clan(user_id,massage):
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE clan_name IS ")
        return cur.fetchall()





    

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    bot.reply_to(message, "lets start")

@bot.message_handler(commands=['clan'])
def set_clan(message):
    parts = message.text.split()

    if len(parts) < 2:
        bot.reply_to(message, "Usage: /clan <name>")
        return

    clan_name = parts[1].lower()
    get_clan(message.chat.id)
    add_clan(message.chat.id, clan_name)
    bot.reply_to(message, "Clan added!")


@bot.message_handler(commands=['masagge'])
def start(message):
    parts = message.text.split()
    massage = parts[1].lower()
    mas = get_clan(message.chat.id)



    bot.reply_to(message, mas ,"you send massage to your clan")


if __name__ == "__main__":
    setup_database()
    print("Bot running...")
    bot.polling()