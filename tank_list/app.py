import requests

API_KEY = "1c67a69b2758f598f6edab23ca7dbb7c"
NICKNAME = "Sagmanchu"
REGION = "eu"

BASE = f"https://api.worldoftanks.{REGION}/wot"


def get_account_id(nickname):
    r = requests.get(
        f"{BASE}/account/list/",
        params={
            "application_id": API_KEY,
            "search": nickname,
            "limit": 1
        }
    ).json()

    if r.get("status") != "ok" or not r.get("data"):
        print("Account lookup error:", r)
        return None

    return str(r["data"][0]["account_id"])


def get_player_tanks(account_id):
    r = requests.get(
        f"{BASE}/account/tanks/",
        params={
            "application_id": API_KEY,
            "account_id": account_id
        }
    ).json()

    if r.get("status") != "ok":
        print("Tank list error:", r)
        return []

    return [str(t["tank_id"]) for t in r["data"][account_id]]


def get_vehicle_info(tank_ids):
    tanks = {}

    CHUNK = 50

    for i in range(0, len(tank_ids), CHUNK):
        chunk = tank_ids[i:i+CHUNK]

        r = requests.get(
            f"{BASE}/encyclopedia/vehicles/",
            params={
                "application_id": API_KEY,
                "tank_id": ",".join(chunk)
            }
        ).json()

        if r.get("status") != "ok":
            print("Vehicle API error:", r)
            continue

        tanks.update(r.get("data", {}))

    return tanks


account_id = get_account_id(NICKNAME)

if not account_id:
    exit()

tank_ids = get_player_tanks(account_id)

vehicle_data = get_vehicle_info(tank_ids)

print(f"\nTier X tanks owned by {NICKNAME}:\n")

for tid in tank_ids:
    tank = vehicle_data.get(tid)

    if tank and tank["tier"] == 10:
        print(f"{tank['name']} ({tank['type']})")