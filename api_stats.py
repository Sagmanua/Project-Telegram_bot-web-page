import requests

# =========================
# CONFIG
# =========================
APP_ID = "02a11c34c34f9a3f73766e3646a1e21a"
PLAYER = ""
REGION = "eu"  # eu | na | asia


# =========================
# FUNCTIONS
# =========================
def get_account_id():
    url = f"https://api.worldoftanks.{REGION}/wot/account/list/"
    params = {
        "application_id": APP_ID,
        "search": PLAYER
    }

    r = requests.get(url, params=params)
    r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        raise Exception("Player not found")

    return data[0]["account_id"]


def get_player_stats(account_id):
    url = f"https://api.worldoftanks.{REGION}/wot/account/info/"
    params = {
        "application_id": APP_ID,
        "account_id": account_id
    }

    r = requests.get(url, params=params)
    r.raise_for_status()

    return r.json()["data"][str(account_id)]


# =========================
# MAIN
# =========================
def main_local(player_name):
  if __name__ == "__main__":
      print("Fetching WoT player stats...")

      account_id = get_account_id()
      stats = get_player_stats(account_id)

      all_stats = stats["statistics"]["all"]
      team_stats = stats["statistics"]["team"]

      result = {
          "nickname": stats["nickname"],
          "battles": all_stats["battles"],
          "wins": all_stats["wins"],
          "frags": all_stats["frags"],
          "battles": team_stats["battles"],
          "winrate": round(all_stats["wins"] / all_stats["battles"] * 100, 2),
          "avg_damage": round(all_stats["damage_dealt"] / all_stats["battles"])
      }

      print("Result:")
      print(result)

while True:
    PLAYER = input("Enter WoT player name (or 'quit' to exit): ").strip()
    if PLAYER.lower() == "quit":
        break
    try:
        main_local(PLAYER)
    except Exception as e:
        print("Error:", e)



