import requests
import time

APP_ID = "1c67a69b2758f598f6edab23ca7dbb7c"
CLAN_TAG = "PZE-H"

def get_clan_id_by_tag(tag):
    # Search for the clan by its tag to get the numerical ID
    search_url = f"https://api.worldoftanks.eu/wot/clans/list/?application_id={APP_ID}&search={tag}"
    response = requests.get(search_url).json()
    if response['status'] == 'ok' and response['data']:
        for clan in response['data']:
            if clan['tag'] == tag:
                return clan['clan_id']
    return None

def get_online_members():
    # 1. Convert Tag to ID
    clan_id = get_clan_id_by_tag(CLAN_TAG)
    if not clan_id:
        return "Clan not found."

    # 2. Get all member IDs
    clan_url = f"https://api.worldoftanks.eu/wot/clans/info/?application_id={APP_ID}&clan_id={clan_id}"
    clan_data = requests.get(clan_url).json()
    if clan_data['status'] != 'ok':
        return "Error fetching clan data."

    members = clan_data['data'][str(clan_id)]['members']
    account_ids = ",".join([str(m['account_id']) for m in members])

    # 3. Request 'last_battle_time' instead of 'online'
    status_url = f"https://api.worldoftanks.eu/wot/account/info/?application_id={APP_ID}&account_id={account_ids}&fields=nickname,last_battle_time"
    status_data = requests.get(status_url).json()

    active_list = []
    if status_data['status'] == 'ok':
        current_time = time.time()
        for acc_id, info in status_data['data'].items():
            # Make sure info exists and has a last battle time
            if info and info.get('last_battle_time'):
                # Check if the player had a battle in the last 2 hours (7200 seconds)
                time_since_last_battle = current_time - info['last_battle_time']
                if time_since_last_battle < 7200: 
                    active_list.append(info['nickname'])

    return active_list

if __name__ == "__main__":
    active_players = get_online_members()
    print(f"Recently active players: {active_players}")