import requests

# =========================
# CONFIG
# =========================
APP_ID = "02a11c34c34f9a3f73766e3646a1e21a"
REGION = "eu"  # eu | na | asia

# =========================
# FUNCTIONS
# =========================
def get_clan_id(clan_name):
    """Fetch the clan ID using the clan name or tag."""
    # Use 'clans' plural for the official WG API endpoint
    url = f"https://api.worldoftanks.{REGION}/wot/clans/list/"
    params = {
        "application_id": APP_ID,
        "search": clan_name
    }

    r = requests.get(url, params=params)
    r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        raise Exception(f"Clan '{clan_name}' not found")

    # FIX: Corrected from 'account_id' to 'clan_id'
    return data[0]["clan_id"]


def get_clan_stats(clan_id):
    """Fetch detailed clan stats using the clan ID."""
    url = f"https://api.worldoftanks.{REGION}/wot/clans/info/"
    params = {
        "application_id": APP_ID,
        "clan_id": clan_id,
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    
    # Accessing the specific clan data via the clan_id string key
    return r.json()["data"][str(clan_id)]


def fetch_and_display_stats(clan_name):
    """Main function to fetch and print clan statistics."""
    clan_id = get_clan_id(clan_name)
    stats = get_clan_stats(clan_id)

    print(f"\n--- Statistics for {stats['name']} [{stats['tag']}] ---")

    # Clan stats are often nested under 'private' or calculated from members
    # For general public info:
    members_count = stats.get("members_count", 0)
    created_at = stats.get("created_at", "N/A")

    result = {
        "Name": stats["name"],
        "Tag": stats["tag"],
        "Clan ID": stats["clan_id"],
        "Members": members_count,
        "Motto": stats.get("motto", "No motto"),
        "Leader": stats.get("leader_name", "N/A")
    }

    for k, v in result.items():
        print(f"{k}: {v}")
    
    print("\nNote: Performance stats (WN8/Winrate) are community-driven")
    print("and may require extra API calls to individual member data.")
    print("-" * 40 + "\n")


# =========================
# RUN LOOP
# =========================
if __name__ == "__main__":
    print(f"Connected to Region: {REGION.upper()}")
    while True:
        user_input = input("Enter WoT CLAN name or TAG (or 'quit' to exit): ").strip()
        if user_input.lower() == "quit":
            break
        try:
            fetch_and_display_stats(user_input)
        except Exception as e:
            print(f"Error: {e}")