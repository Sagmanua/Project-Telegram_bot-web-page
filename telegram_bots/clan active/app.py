import telebot
import requests
import time

# --- Configuration ---
API_TOKEN = '8340925625:AAFJcl_MmBtRoBitmJfUW_Bcz72Wymq-gm8' # Get this from @BotFather
APP_ID = "1c67a69b2758f598f6edab23ca7dbb7c"

bot = telebot.TeleBot(API_TOKEN)




def get_clan_id_by_tag(tag):
    """Searches for a clan by its tag and returns the numerical ID."""
    search_url = f"https://api.worldoftanks.eu/wot/clans/list/?application_id={APP_ID}&search={tag}"
    try:
        response = requests.get(search_url).json()
        if response['status'] == 'ok' and response['data']:
            for clan in response['data']:
                if clan['tag'].upper() == tag.upper():
                    return clan['clan_id']
    except Exception as e:
        print(f"Error searching clan: {e}")
    return None

def get_active_members(clan_tag):
    """Fetches members who had a battle in the last 2 hours."""
    # 1. Convert Tag to ID
    clan_id = get_clan_id_by_tag(clan_tag)
    if not clan_id:
        return f"❌ <b>Clan [{clan_tag.upper()}] not found.</b>"

    # 2. Get all member IDs
    clan_url = f"https://api.worldoftanks.eu/wot/clans/info/?application_id={APP_ID}&clan_id={clan_id}"
    clan_data = requests.get(clan_url).json()
    
    if clan_data['status'] != 'ok' or not clan_data['data'][str(clan_id)]:
        return "❌ <b>Error:</b> Could not fetch clan data from WG API."

    members = clan_data['data'][str(clan_id)]['members']
    if not members:
        return f"The clan <b>[{clan_tag.upper()}]</b> exists but has no members."

    account_ids = ",".join([str(m['account_id']) for m in members])

    # 3. Request account info (Last Battle Time)
    status_url = f"https://api.worldoftanks.eu/wot/account/info/?application_id={APP_ID}&account_id={account_ids}&fields=nickname,last_battle_time"
    status_data = requests.get(status_url).json()

    active_list = []
    if status_data['status'] == 'ok':
        current_time = time.time()
        for acc_id, info in status_data['data'].items():
            if info and info.get('last_battle_time'):
                # Check if the player had a battle in the last 2 hours (7200 seconds)
                time_diff = current_time - info['last_battle_time']
                if time_diff < 7200:
                    minutes_ago = int(time_diff // 60)
                    active_list.append(f"• <b>{info['nickname']}</b> ({minutes_ago}m ago)")

    if not active_list:
        return f"No players from <b>[{clan_tag.upper()}]</b> were active in the last 2 hours."
    
    header = f"🔥 <b>Recently Active in [{clan_tag.upper()}]:</b>\n\n"
    return header + "\n".join(active_list)

# --- Bot Command Handlers ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "Welcome! I can check which clan members are currently active.\n\n"
        "<b>Usage:</b>\n"
        "<code>/clan_online TAG</code>\n\n"
        "<i>Example: /clan_online PZE-H</i>"
    )
    bot.reply_to(message, help_text, parse_mode="HTML")

@bot.message_handler(commands=['clan_online'])
def handle_clan_query(message):
    try:
        # Extract command arguments
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Please provide a clan tag.\nExample: <code>/clan_online PZE-H</code>", parse_mode="HTML")
            return

        clan_tag = parts[1]
        # Send initial status message
        status_msg = bot.reply_to(message, f"🛰 Scanning <b>{clan_tag.upper()}</b>...", parse_mode="HTML")
        
        # Get the results
        result_text = get_active_members(clan_tag)
        
        # Update the message with the results
        bot.edit_message_text(
            chat_id=status_msg.chat.id, 
            message_id=status_msg.message_id, 
            text=result_text, 
            parse_mode="HTML"
        )
        
    except Exception as e:
        print(f"General Error: {e}")
        bot.send_message(message.chat.id, "🛑 An error occurred while processing your request.")

if __name__ == "__main__":
    print("Bot started. Press Ctrl+C to stop.")
    bot.infinity_polling()