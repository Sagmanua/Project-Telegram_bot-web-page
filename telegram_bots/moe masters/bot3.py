import json
import telebot
import logging
from rapidfuzz import process, fuzz

# Set up basic logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# Load the JSON data into memory
def load_data():
    try:
        with open('combined_data.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error("The file combined_data.json was not found.")
        return {"mastery": [], "gunmarks": []}

DATA = load_data()

# Initialize the bot
BOT_TOKEN = "8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8"
bot = telebot.TeleBot(BOT_TOKEN)

def find_tank_data(category: str, tank_name: str):
    """Helper function to find a tank using fuzzy matching."""
    # 1. Get all tank names from the specified category
    tank_list = [item.get("tank", "") for item in DATA.get(category, [])]
    
    if not tank_list:
        return None

    # 2. Use rapidfuzz to find the best match
    # 'score_cutoff' ensures we don't return a bad result if the input is too random
    match = process.extractOne(
        tank_name, 
        tank_list, 
        scorer=fuzz.WRatio, 
        score_cutoff=70
    )
    if match:
        best_match_name = match[0]
        # Find the original object in DATA based on the matched name
        for item in DATA.get(category, []):
            if item.get("tank") == best_match_name:
                return item
                
    return None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Send a message when the command /start or /help is issued."""
    welcome_message = (
        "Hello! I am your Tank Stats Bot.\n\n"
        "Use the following commands:\n"
        "🏆 <code>/mastery &lt;tank_name&gt;</code> - Get mastery requirements\n"
        "🎯 <code>/gunmark &lt;tank_name&gt;</code> - Get gun mark requirements\n\n"
        "Example: <code>/mastery Tiger I</code>"
    )
    bot.reply_to(message, welcome_message, parse_mode='HTML')

@bot.message_handler(commands=['mastery'])
def handle_mastery(message):
    """Handle the /mastery command."""
    # Split the message to separate the command from the tank name
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        bot.reply_to(message, "Please provide a tank name. Example: <code>/mastery Tiger I</code>", parse_mode='HTML')
        return

    tank_name = parts[1]
    tank_data = find_tank_data("mastery", tank_name)

    if tank_data:
        # Filter out empty strings from the values list
        values = [v for v in tank_data.get("values", []) if v]
        
        response = f"🏆 <b>Mastery Values for {tank_data['tank']}</b>\n\n"
        
        # Standard WoT mastery labels
        labels = ["Class III", "Class II", "Class I", "Ace Tanker"]
        for i, val in enumerate(values):
            label = labels[i] if i < len(labels) else f"Value {i+1}"
            response += f"• <b>{label}:</b> {val}\n"
            
        bot.reply_to(message, response, parse_mode='HTML')
    else:
        bot.reply_to(message, f"Sorry, I couldn't find mastery data for '<b>{tank_name}</b>'.", parse_mode='HTML')

@bot.message_handler(commands=['gunmark'])
def handle_gunmark(message):
    """Handle the /gunmark command."""
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        bot.reply_to(message, "Please provide a tank name. Example: <code>/gunmark M103M</code>", parse_mode='HTML')
        return

    tank_name = parts[1]
    tank_data = find_tank_data("gunmarks", tank_name)

    if tank_data:
        # Filter out empty strings from the values list
        values = [v for v in tank_data.get("values", []) if v]
        
        response = f"🎯 <b>Gun Mark Values for {tank_data['tank']}</b>\n\n"
        
        # Standard WoT gunmark labels
        labels = ["65% (1 Mark)", "85% (2 Marks)", "95% (3 Marks)", "100%"]
        for i, val in enumerate(values):
            label = labels[i] if i < len(labels) else f"Value {i+1}"
            response += f"• <b>{label}:</b> {val}\n"
            
        bot.reply_to(message, response, parse_mode='HTML')
    else:
        bot.reply_to(message, f"Sorry, I couldn't find gun mark data for '<b>{tank_name}</b>'.", parse_mode='HTML')

if __name__ == '__main__':
    logging.info("Bot is starting...")
    # Using infinity_polling ensures the bot restarts if it throws an error
    bot.infinity_polling()