import sqlite3
import telebot
from telebot import types
from datetime import datetime, timedelta
import threading
import time

# ================= CONFIG =================

DATABASE = "tasks.db"
TOKEN = ""

# 👑 Admin Telegram IDs
ADMINS = {1083670850}  # <-- replace with your Telegram user_id

bot = telebot.TeleBot(TOKEN)

def is_admin(user_id):
    return user_id in ADMINS

# ================= DATABASE =================

def setup_database():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            due_date TEXT,
            completed INTEGER DEFAULT 0
        )
        """)

        conn.commit()


def add_user(user_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )

def get_all_users():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        return [row[0] for row in cur.fetchall()]


def add_task(user_id, description, due_date):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute(
            "INSERT INTO tasks (user_id, description, due_date, completed) VALUES (?, ?, ?, 0)",
            (user_id, description, due_date)
        )


def delete_task(task_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))


def mark_completed(task_id):
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("UPDATE tasks SET completed=1 WHERE task_id=?", (task_id,))


def get_tasks():
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT task_id, description, due_date, completed FROM tasks")
        return cur.fetchall()


def get_upcoming_tasks():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT description FROM tasks WHERE due_date=? AND completed=0",
            (tomorrow,)
        )
        return cur.fetchall()

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    role = "👑 Admin" if is_admin(message.chat.id) else "👀 Viewer"

    bot.reply_to(
        message,
        f"Welcome to Task Manager Bot!\nRole: {role}\n\n"
        "Commands:\n"
        "/list - View tasks\n"
        "Admins only:\n"
        "/add <task> <YYYY-MM-DD>\n"
        "/delete <task_id>"
    )


# -------- ADD TASK (ADMIN ONLY) --------

@bot.message_handler(commands=['add'])
def add_task_command(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not allowed to add tasks.")
        return

    try:
        _, *task_parts, due_date = message.text.split()
        task = " ".join(task_parts)

        datetime.strptime(due_date, "%Y-%m-%d")

        add_task(message.chat.id, task, due_date)
        bot.reply_to(message, f"✅ Task added:\n{task}\nDue: {due_date}")

    except:
        bot.reply_to(
            message,
            "Usage:\n/add <task description> <YYYY-MM-DD>\n"
            "Example:\n/add Prepare report 2026-02-02"
        )


# -------- LIST TASKS (EVERYONE) --------

@bot.message_handler(commands=['list'])
def list_tasks(message):
    tasks = get_tasks()

    if not tasks:
        bot.send_message(message.chat.id, "📭 No tasks available.")
        return

    for task_id, description, due_date, completed in tasks:
        status = "✅" if completed else "❌"

        markup = types.InlineKeyboardMarkup()

        if is_admin(message.chat.id) and not completed:
            markup.add(
                types.InlineKeyboardButton(
                    text="Mark as Done",
                    callback_data=f"done_{task_id}"
                )
            )

        bot.send_message(
            message.chat.id,
            f"{task_id}. {status} {description}\nDue: {due_date}",
            reply_markup=markup if markup.keyboard else None
        )


# -------- MARK DONE (ADMIN ONLY) --------

@bot.callback_query_handler(func=lambda call: call.data.startswith("done_"))
def done_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Admins only!")
        return

    task_id = int(call.data.split("_")[1])
    mark_completed(task_id)

    bot.answer_callback_query(call.id, "✅ Task completed!")
    bot.edit_message_text(
        "✅ Task marked as completed.",
        call.message.chat.id,
        call.message.message_id
    )


# -------- DELETE TASK (ADMIN ONLY) --------

@bot.message_handler(commands=['delete'])
def delete_task_command(message):
    if not is_admin(message.chat.id):
        bot.reply_to(message, "❌ You are not allowed to delete tasks.")
        return

    try:
        task_id = int(message.text.split()[1])
        delete_task(task_id)
        bot.reply_to(message, f"🗑 Task {task_id} deleted.")
    except:
        bot.reply_to(message, "Usage: /delete <task_id>")


# ================= REMINDER THREAD =================

def send_reminders():
    while True:
        tasks = get_upcoming_tasks()
        all_users = get_all_users()
        
        if tasks and all_users:
            for (description,) in tasks:
                for user_id in all_users:
                    try:
                        bot.send_message(user_id, f"⏰ Reminder: '{description}' is due tomorrow!")
                    except Exception as e:
                        print(f"Could not send message to {user_id}: {e}")
        
        # Wait for 1 hour (3600 seconds) before checking again
        time.sleep(3600)


# ================= START BOT =================

setup_database()

threading.Thread(target=send_reminders, daemon=True).start()

bot.polling(none_stop=True)
