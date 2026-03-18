import telebot

bot = telebot.TeleBot('8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8')

@bot.message_handler(content_types=['document'])
def catch_id(message):
    print(f"--- COPY THIS FILE ID ---")
    print(message.document.file_id)
    print(f"--------------------------")
    bot.reply_to(message, "ID captured! Check your terminal.")

print("Bot is waiting for you to send the file...")
bot.polling()