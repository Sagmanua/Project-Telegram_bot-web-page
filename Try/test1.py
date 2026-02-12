import os
import json
import re

BASE_DIR = r"C:\Users\bestp\Desktop\Try"
VEHICLES_FOLDER = os.path.join(BASE_DIR, "vehicles")
OUTPUT_FILE = os.path.join(BASE_DIR, "full_vehicle_database2.json")

def extract_nested_value(content, parent_tag, child_tag):
    """
    Finds the section between <parent_tag> and </parent_tag>, 
    then finds the <child_tag> inside it.
    """
    parent_pattern = rf"<{parent_tag}>([\s\S]*?)</{parent_tag}>"
    parent_match = re.search(parent_pattern, content)
    if parent_match:
        inner_content = parent_match.group(1)
        child_pattern = rf"<{child_tag}>([^<]+)</{child_tag}>"
        child_match = re.search(child_pattern, inner_content)
        return child_match.group(1).strip() if child_match else None
    return None

def extract_simple(text, tag):
    pattern = rf"<{tag}>([^<]+)</{tag}>"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None

def parse_vehicle_file(file_path, nation):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if "<maxHealth>" not in content:
            return None

        # Targeted extraction for chassis dispersion
        movement_disp = extract_nested_value(content, "shotDispersionFactors", "vehicleMovement")
        rotation_disp = extract_nested_value(content, "shotDispersionFactors", "vehicleRotation")

        return {
            "nation": nation,
            "internal_name": os.path.splitext(os.path.basename(file_path))[0],
            "tier": extract_simple(content, "level"),
            "hp": extract_simple(content, "maxHealth"),
            "chassis_dispersion": {
                "movement": movement_disp,
                "rotation": rotation_disp
            },
            "speed_limits": {
                "forward": extract_simple(content, "forward"),
                "backward": extract_simple(content, "backward")
            },
            "invisibility_stats": {
                "stationary": extract_simple(content, "still"),
                "moving": extract_simple(content, "moving")
            }
        }
    except Exception:
        return None

def main():
    all_tanks = []
    print("🚀 Extracting data with corrected dispersion tags...")

    for root_dir, _, files in os.walk(VEHICLES_FOLDER):
        nation = os.path.normpath(root_dir).split(os.sep)[-1]
        for file in files:
            if file.endswith(".xml") and not any(x in file for x in ["_cl.xml", "collision"]):
                data = parse_vehicle_file(os.path.join(root_dir, file), nation)
                if data:
                    all_tanks.append(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_tanks, f, indent=4)
        
    print(f"✅ SUCCESS! Database saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()