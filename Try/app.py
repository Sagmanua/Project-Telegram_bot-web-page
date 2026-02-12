import os
import json
import re

# We set the absolute folder path here
BASE_DIR = r"C:\Users\bestp\Desktop\Try"
VEHICLES_FOLDER = os.path.join(BASE_DIR, "vehicles")
# This forces the JSON to save exactly in your 'Try' folder
OUTPUT_FILE = os.path.join(BASE_DIR, "camo_database.json")

def extract_value(text, tag):
    pattern = rf"<{tag}>([^<]+)</{tag}>"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None

def parse_vehicle_file(file_path, nation):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        hp = extract_value(content, "maxHealth")
        if not hp:
            return None

        tank_data = {
            "nation": nation,
            "internal_name": os.path.splitext(os.path.basename(file_path))[0],
            "tier": extract_value(content, "level"),
            "hp": hp,
            "view_range": extract_value(content, "circularVisionRadius"),
            "camouflage": {
                "stationary": extract_value(content, "still"),
                "moving": extract_value(content, "moving"),
            }
        }
        return tank_data
    except Exception:
        return None

def main():
    all_tanks = []
    
    if not os.path.exists(VEHICLES_FOLDER):
        print(f"❌ Error: Could not find folder at {VEHICLES_FOLDER}")
        return

    print(f"🚀 Scanning: {VEHICLES_FOLDER}")

    for root_dir, _, files in os.walk(VEHICLES_FOLDER):
        parts = os.path.normpath(root_dir).split(os.sep)
        nation = parts[-1] if parts else "unknown"

        for file in files:
            if file.endswith(".xml") and not any(x in file for x in ["_cl.xml", "collision"]):
                file_path = os.path.join(root_dir, file)
                tank_data = parse_vehicle_file(file_path, nation)
                if tank_data:
                    all_tanks.append(tank_data)

    # WRITE THE FILE
    try:
        print(f"💾 Attempting to save to: {OUTPUT_FILE}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_tanks, f, indent=4)
        
        # Double check if file exists after writing
        if os.path.exists(OUTPUT_FILE):
            print(f"✅ SUCCESS! File created. Size: {os.path.getsize(OUTPUT_FILE)} bytes")
        else:
            print("❌ Error: File was not created even though write command finished.")
            
    except Exception as e:
        print(f"❌ Critical Error saving file: {e}")

if __name__ == "__main__":
    main()