import requests
from bs4 import BeautifulSoup

API_KEY = "1c67a69b2758f598f6edab23ca7dbb7c"
REGION = "eu"   # eu / na / asia


def find_tank_id(tank_name):
    url = f"https://api.worldoftanks.{REGION}/wot/encyclopedia/vehicles/"
    params = {
        "application_id": API_KEY,
        "search": tank_name,
        "limit": 5
    }

    r = requests.get(url, params=params).json()

    if r["status"] != "ok" or not r["data"]:
        return None

    # Show matches and let user choose
    tanks = list(r["data"].items())

    print("\nMatches found:")
    for i, (tank_id, info) in enumerate(tanks):
        print(f"{i+1}. {info['name']} (Tier {info['tier']})")

    choice = int(input("Select tank number: ")) - 1
    tank_id, info = tanks[choice]

    return tank_id, info["name"]


def get_moe_data(tank_id):
    url = f"https://tomato.gg/tank-stats/{REGION}/{tank_id}"
    headers = {"User-Agent": "Mozilla/5.0"}  # avoids some blocks

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        print("Could not fetch Tomato.gg page.")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()

    return text


def main():
    while True:
        tank_name = input("\nEnter tank name (or exit): ")
        if tank_name.lower() == "exit":
            break

        result = find_tank_id(tank_name)
        if not result:
            print("Tank not found.")
            continue

        tank_id, real_name = result
        print(f"\nFetching MoE data for {real_name}...")

        data = get_moe_data(tank_id)

        if data:
            print("\n--- Raw Page Text (preview) ---")
            print(data[:1500])


if __name__ == "__main__":
    main()