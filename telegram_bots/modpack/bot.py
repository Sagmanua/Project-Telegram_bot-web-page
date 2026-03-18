import telebot
import os
from telebot import types

# 1. Initialize your bot
bot = telebot.TeleBot('8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8')

# 2. Define the path (Make sure this file is in the SAME folder as this script)
LOCAL_MODPACK_PATH = "Aslains_WoT_Modpack_Installer_v.2.2.0.0_13.exe"
WEBSITE_URL = "https://wgmods.net/46/"

@bot.message_handler(commands=['modpack'])
def send_modpack_options(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_download = types.InlineKeyboardButton("Download from Telegram", callback_data="dl_tg")
    btn_website = types.InlineKeyboardButton("Go to Website", url=WEBSITE_URL)
    markup.add(btn_download, btn_website)
    
    bot.send_message(message.chat.id, "Choose how you want to get the modpack:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "dl_tg")
def handle_download_callback(call):
    bot.answer_callback_query(call.id, "Checking server files...")
    
    # Check if the file exists
    if os.path.exists(LOCAL_MODPACK_PATH):
        bot.send_message(call.message.chat.id, "Uploading to Telegram... this may take a moment.")
        
        try:
            with open(LOCAL_MODPACK_PATH, 'rb') as file_to_send:
                bot.send_document(
                    call.message.chat.id, 
                    file_to_send, 
                    caption="✅ Here is the Aslain's Modpack installer!"
                )
        except Exception as e:
            bot.send_message(call.message.chat.id, f"Upload failed: {e}")
    else:
        # This triggers if the filename in the code doesn't match the file in your folder
        bot.send_message(call.message.chat.id, f"❌ Error: File '{LOCAL_MODPACK_PATH}' not found on the server.")

print("Bot is running...")
bot.polling()