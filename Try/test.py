import os
import json
import re

BASE_DIR = r"C:\Users\bestp\Desktop\Try"
VEHICLES_FOLDER = os.path.join(BASE_DIR, "vehicles")
OUTPUT_FILE = os.path.join(BASE_DIR, "full_vehicle_database.json")

def extract_value(text, tag):
    pattern = rf"<{tag}>([^<]+)</{tag}>"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None

def parse_vehicle_file(file_path, nation):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Check for maxHealth - if not there, it's not a tank file
        hp = extract_value(content, "maxHealth")
        if not hp:
            return None

        # Build a complete dictionary of all data in the file
        tank_data = {
            "nation": nation,
            "internal_name": os.path.splitext(os.path.basename(file_path))[0],
            "tier": extract_value(content, "level"),
            "hp": hp,
            "view_range": extract_value(content, "circularVisionRadius"),
            "speed_limits": {
                "forward": extract_value(content, "forward"),
                "backward": extract_value(content, "backward")
            },
            "invisibility_stats": {
                "stationary": extract_value(content, "still"),
                "moving": extract_value(content, "moving"),
                "fire_penalty": extract_value(content, "firePenalty"),
                "camo_bonus": extract_value(content, "camouflageBonus")
            },
            "engine": {
                "power": extract_value(content, "smplEnginePower"),
                "name": extract_value(content, "engines") # Grab engine ID
            },
            "armor": {
                "hull": extract_value(content, "armor"), # Note: Raw string of armor values
                "primary_armor": extract_value(content, "primaryArmor")
            },
            "gun_performance": {
                "reload_time": extract_value(content, "reloadTime"),
                "aiming_time": extract_value(content, "aimingTime"),
                "shot_dispersion": extract_value(content, "shotDispersionRadius")
            }
        }
        return tank_data
    except Exception:
        return None

def main():
    all_tanks = []
    if not os.path.exists(VEHICLES_FOLDER):
        print(f"❌ Error: Path not found: {VEHICLES_FOLDER}")
        return

    print(f"🚀 Extracting FULL data from: {VEHICLES_FOLDER}")

    for root_dir, _, files in os.walk(VEHICLES_FOLDER):
        parts = os.path.normpath(root_dir).split(os.sep)
        nation = parts[-1] if parts else "unknown"

        for file in files:
            if file.endswith(".xml") and not any(x in file for x in ["_cl.xml", "collision"]):
                file_path = os.path.join(root_dir, file)
                tank_data = parse_vehicle_file(file_path, nation)
                if tank_data:
                    all_tanks.append(tank_data)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_tanks, f, indent=4)
        
        if os.path.exists(OUTPUT_FILE):
            print(f"✅ DONE! Saved {len(all_tanks)} tanks with full details.")
            print(f"📂 Location: {OUTPUT_FILE}")
            
    except Exception as e:
        print(f"❌ Error saving: {e}")

if __name__ == "__main__":
    main()