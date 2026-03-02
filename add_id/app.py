import json
import requests
import urllib.parse
import time
API_KEY = "1c67a69b2758f598f6edab23ca7dbb7c"
REGION = "eu"   # change if needed (eu, com, asia)

INPUT_FILE = "tanks_data.json"
OUTPUT_FILE = "tanks_with_ids.json"

BASE_URL = f"https://api.worldoftanks.{REGION}/wot/encyclopedia/vehicles/"


def get_tank_id(tank_name):
    params = {
        "application_id": API_KEY,
        "search": tank_name
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()

        if data.get("status") != "ok":
            print(f"API error for {tank_name}")
            return None

        vehicles = data.get("data", {})

        # Exact match only
        for tank_data in vehicles.values():
            if tank_data["name"].strip().lower() == tank_name.strip().lower():
                return tank_data["tank_id"]

        # No exact match found
        print(f"Skipped (no exact match): {tank_name}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Skipped (request failed): {tank_name} -> {e}")
        return None


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        tanks = json.load(f)

    for tank in tanks:
        name = tank["full_name"]
        print(f"Searching ID for: {name}")

        tank_id = get_tank_id(name)

        if tank_id is not None:
            tank["tank_id"] = tank_id
            print(f"✔ Found: {name} -> {tank_id}")
        else:
            print(f"✘ Skipped: {name}")
            # Do NOT crash, just skip
            # Optionally you can leave existing tank_id untouched

        time.sleep(0.2)  # prevent API rate limit

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(tanks, f, indent=4)

    print("Done. IDs added to file.")


if __name__ == "__main__":
    main()