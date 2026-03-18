import telebot
from telebot import types

# 1. Setup
API_TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8'
bot = telebot.TeleBot(API_TOKEN)

# 2. Configuration
# PASTE THE ID YOU GOT FROM PHASE 1 HERE:
SAVED_FILE_ID = "BQACAgIAAxkBAAIDlmm5TT9gsXXxtiJzkn9czeEsgyg6AAK9lQAC57jQSY8Ia8KsCLmgOgQ" 
WEBSITE_URL = "https://wgmods.net/46/"

@bot.message_handler(commands=['start', 'modpack'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Button 1: Download directly (Fast, no upload wait)
    btn_download = types.InlineKeyboardButton("📥 Download from Telegram", callback_data="dl_tg")
    
    # Button 2: External Link
    btn_website = types.InlineKeyboardButton("🌐 Go to Website", url=WEBSITE_URL)
    
    markup.add(btn_download, btn_website)
    
    bot.send_message(
        message.chat.id, 
        "<b>Aslain's WoT Modpack</b>\n\nChoose your preferred download method:", 
        parse_mode='HTML', 
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "dl_tg")
def handle_download(call):
    # Check if you forgot to update the ID
    if "PASTE_YOUR_FILE_ID" in SAVED_FILE_ID:
        bot.answer_callback_query(call.id, "Error: File ID not set in code.", show_alert=True)
        return

    # Let the user know it's coming
    bot.answer_callback_query(call.id, "Sending file...")
    
    try:
        # This sends the file instantly because it's already on Telegram servers
        bot.send_document(
            call.message.chat.id, 
            SAVED_FILE_ID, 
            caption="✅ <b>Aslain's Modpack Installer</b>\nReady to install.",
            parse_mode='HTML'
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Failed to send: {e}")

print("Bot is live! Type /modpack in Telegram.")
bot.polling()