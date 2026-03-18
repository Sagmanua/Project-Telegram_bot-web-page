import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
bot = telebot.TeleBot(TOKEN)

# --- 1. MAIN MENU ---
@bot.message_handler(commands=['start'])
def main_menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📂 Products", callback_data="menu_products"))
    markup.add(InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"))
    
    bot.send_message(message.chat.id, "Welcome! Choose a category:", reply_markup=markup)

# --- 2. CALLBACK HANDLER (The "Navigation" Logic) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    
    # --- ENTERING THE PRODUCTS SUB-MENU ---
    if call.data == "menu_products":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🍎 Fruit", callback_data="prod_fruit"),
                   InlineKeyboardButton("🥦 Veggies", callback_data="prod_veg"))
        markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main"))
        
        bot.edit_message_text("Which products would you like to see?", 
                              call.message.chat.id, 
                              call.message.message_id, 
                              reply_markup=markup)

    # --- ENTERING THE SETTINGS SUB-MENU ---
    elif call.data == "menu_settings":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔔 Notifications: ON", callback_data="toggle_notif"))
        markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_to_main"))
        
        bot.edit_message_text("Settings Menu:", 
                              call.message.chat.id, 
                              call.message.message_id, 
                              reply_markup=markup)

    # --- RETURNING TO MAIN MENU ---
    elif call.data == "back_to_main":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📂 Products", callback_data="menu_products"))
        markup.add(InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"))
        
        bot.edit_message_text("Welcome! Choose a category:", 
                              call.message.chat.id, 
                              call.message.message_id, 
                              reply_markup=markup)
    
    # Acknowledge the click so the loading icon disappears
    bot.answer_callback_query(call.id)

print("Bot is running...")
bot.infinity_polling()