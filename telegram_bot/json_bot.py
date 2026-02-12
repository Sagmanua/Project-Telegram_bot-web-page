import telebot
import json

# Initialize your bot with your token
bot = telebot.TeleBot(":-gm8")

# Function to load data from JSON
def load_tank_data():
    with open('tanks.json', 'r') as file:
        return json.load(file)

@bot.message_handler(commands=['tank'])
def send_tank_info(message):
    # Split the message to get the tank name
    # Example: "/tank ebr105" -> ["/tank", "ebr105"]
    text_parts = message.text.split()
    
    if len(text_parts) < 2:
        bot.reply_to(message, "Please provide a tank name! Usage: /tank ebr105")
        return

    tank_name = text_parts[1].lower()
    tanks = load_tank_data()

    if tank_name in tanks:
        data = tanks[tank_name]
        caption = (
            f"🛡 *{data['full_name']}*\n"
            f"💥 Damage: {data['damage']}"
        )
        
        # This sends the photo and puts the description as the caption
        bot.send_photo(
            message.chat.id, 
            photo=data['image'], 
            caption=caption, 
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, f"❌ Tank '{tank_name}' not found.")

print("Bot is running...")
bot.infinity_polling()