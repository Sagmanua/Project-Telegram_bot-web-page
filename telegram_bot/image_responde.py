import telebot
import requests
from io import BytesIO

# ================= CONFIG =================
# Reminder: Keep this token private! 
TOKEN = ":-gm8"
bot = telebot.TeleBot(TOKEN)

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Welcome! Use `/image` to test an image or `/local` for a local file.", parse_mode="Markdown")


# ================= BOT json file  =================




# ================= BOT Images =================


@bot.message_handler(commands=['this'])
def clan_command(message):
    # FIXED: Added 'message' as the first argument
    bot.reply_to(message, "ok this is test")

@bot.message_handler(commands=['local'])
def send_local_image(message):
    try:
        with open('stats.png', 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption="Here is your local stats file.")
    except FileNotFoundError:
        bot.reply_to(message, "❌ Error: File 'stats.png' not found in your project folder.")

@bot.message_handler(commands=['image'])
def send_image_example(message):
    # Using Lorem Picsum - a reliable testing site
    image_url = "https://picsum.photos/800/600"
    
    try:
        # 1. Download the image into memory first
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # 2. Use BytesIO to treat the downloaded bytes as a file
            photo_file = BytesIO(response.content)
            bot.send_photo(
                message.chat.id, 
                photo=photo_file, 
                caption="✅ Success! I downloaded this from a URL and sent it to you."
            )
        else:
            bot.reply_to(message, f"❌ Site returned error code: {response.status_code}")
            
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error fetching image: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)