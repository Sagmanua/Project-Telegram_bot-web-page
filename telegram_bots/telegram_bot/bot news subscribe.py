import telebot
import sqlite3
import feedparser
import time
import threading
from datetime import datetime

# --- CONFIG ---
API_TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
RSS_URL = "https://worldoftanks.com/en/rss/news/"
DB_NAME = "wot_users.db"

bot = telebot.TeleBot(API_TOKEN)

# --- DATABASE LOGIC ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS subscribers (chat_id INTEGER PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    conn.commit()
    conn.close()

def add_subscriber(chat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)', (chat_id,))
    conn.commit()
    conn.close()

def remove_subscriber(chat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM subscribers WHERE chat_id = ?', (chat_id,))
    conn.commit()
    conn.close()

def get_subscribers():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT chat_id FROM subscribers')
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_last_link():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key="last_link"')
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def set_last_link(link):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("last_link", ?)', (link,))
    conn.commit()
    conn.close()

# --- BOT COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Commands:\n/news_on - Subscribe\n/news_off - Unsubscribe")

@bot.message_handler(commands=['news_on'])
def subscribe(message):
    add_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "✅ Subscribed to World of Tanks news!")

@bot.message_handler(commands=['news_off'])
def unsubscribe(message):
    remove_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "❌ Unsubscribed. You will no longer receive news.")

# --- THE AUTO-CHECKER ---
def check_news_loop():
    while True:
        # Get current time for the print log
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] Checking WoT API/RSS feed...")

        try:
            feed = feedparser.parse(RSS_URL)
            if feed.entries:
                latest_entry = feed.entries[0]
                latest_link = latest_entry.link
                saved_link = get_last_link()

                if latest_link != saved_link:
                    # Logic for NEW news
                    if saved_link is not None:
                        print(f"[{now}] New news found: {latest_entry.title}")
                        users = get_subscribers()
                        msg = f"🆕 *New WoT News!*\n\n{latest_entry.title}\n{latest_link}"
                        for user_id in users:
                            try:
                                bot.send_message(user_id, msg, parse_mode="Markdown")
                            except Exception as e:
                                print(f"Error sending to {user_id}: {e}")
                    
                    set_last_link(latest_link)
                else:
                    # This tells you it checked but nothing was new
                    print(f"[{now}] No change detected.")

        except Exception as e:
            print(f"[{now}] ERROR: {e}")
        
        # Interval: 300 seconds = 5 minutes
        time.sleep(30) 

# --- RUN ---
if __name__ == "__main__":
    init_db()
    # Start the background thread
    threading.Thread(target=check_news_loop, daemon=True).start()
    print("Bot is starting up... Press Ctrl+C to stop.")
    bot.infinity_polling()