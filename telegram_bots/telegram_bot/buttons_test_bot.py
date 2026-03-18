import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

# 1. Initialize your bot
TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
bot = telebot.TeleBot(TOKEN)

# --- COMMAND: /start (Shows Reply Keyboard) ---
@bot.message_handler(commands=['start'])
def start_command(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = KeyboardButton('Show Inline Buttons')
    btn2 = KeyboardButton('Remove Keyboard')
    markup.add(btn1, btn2)
    
    bot.send_message(
        message.chat.id, 
        "👋 Welcome! I'm a test bot.\nClick the button below to see how Inline buttons work.", 
        reply_markup=markup
    )

# --- HANDLE REPLY BUTTONS ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if message.text == 'Show Inline Buttons':
        # Create Inline Buttons
        markup = InlineKeyboardMarkup()
        btn_a = InlineKeyboardButton("Option A", callback_data="data_a")
        btn_b = InlineKeyboardButton("Option B", callback_data="data_b")
        markup.row(btn_a, btn_b)
        
        bot.send_message(message.chat.id, "Here are the Inline Buttons:", reply_markup=markup)
        
    elif message.text == 'Remove Keyboard':
        # This removes the Reply buttons from the bottom
        bot.send_message(message.chat.id, "Keyboard removed. Type /start to get it back.", reply_markup=ReplyKeyboardRemove())

# --- HANDLE INLINE CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data == "data_a":
        bot.answer_callback_query(call.id, "You chose A!") # Shows a small toast/alert
        bot.send_message(call.message.chat.id, "✅ Logic for Option A triggered.")
        
    elif call.data == "data_b":
        bot.answer_callback_query(call.id) # Just stops the loading spinner
        bot.edit_message_text("You clicked B! Now the original message text has changed.", 
                              call.message.chat.id, 
                              call.message.message_id)

# Start the bot
print("Bot is running...")
bot.infinity_polling()