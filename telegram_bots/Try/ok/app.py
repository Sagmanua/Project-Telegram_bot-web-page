import os
import json
import re

# --- CONFIGURATION ---
# Ensure BASE_DIR is the folder ABOVE the "vehicles" folder
BASE_DIR = r"C:\Project-Telegram_bot-web-page\Try"
VEHICLES_FOLDER = os.path.join(BASE_DIR, "vehicles")
OUTPUT_FILE = os.path.join(BASE_DIR, "full_vehicle_database.json")

# Tanks.gg Crew Constant
CREW_COEFF = 1.043 

def get_tag_value(content, tag):
    """Finds the first occurrence of a tag and returns its text value."""
    pattern = rf"<{tag}>([\s\S]*?)</{tag}>"
    match = re.search(pattern, content)
    if match:
        # Strip internal XML tags if they exist (e.g., <armor>400</armor> -> 400)
        clean_val = re.sub(r'<.*?>', '', match.group(1)).strip()
        return clean_val
    return None

def parse_vehicle_file(file_path, nation):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if "<maxHealth>" not in content:
            return None

        # --- SECTION EXTRACTION ---
        chassis_sec = get_tag_value(content, "chassis") or ""
        turret_sec = get_tag_value(content, "turrets0") or ""
        
        # --- DATA EXTRACTION ---
        hp = get_tag_value(content, "maxHealth")
        tier = get_tag_value(content, "level")
        fw_speed = float(get_tag_value(content, "forward") or 0)
        
        # Chassis stats
        hull_traverse_base = float(get_tag_value(chassis_sec, "rotationSpeed") or 0)
        terrain_raw = get_tag_value(chassis_sec, "terrainResistance") or "1 1 2"
        hard_terrain = float(terrain_raw.split()[0])
        
        mov_factor = float(get_tag_value(chassis_sec, "vehicleMovement") or 0)
        rot_factor = float(get_tag_value(chassis_sec, "vehicleRotation") or 0)

        # Turret & Gun stats
        turret_traverse_base = float(get_tag_value(turret_sec, "rotationSpeed") or 0)
        turret_rot_factor = float(get_tag_value(turret_sec, "turretRotation") or 0)
        
        reload_val = float(get_tag_value(turret_sec, "reloadTime") or 0)
        aim = get_tag_value(turret_sec, "aimingTime")
        acc = get_tag_value(turret_sec, "shotDispersionRadius")

        # --- IMPROVED DAMAGE & DPM EXTRACTION ---
        # Look for damage specifically inside the turret/gun section
        avg_damage = 0
        damage_raw = get_tag_value(turret_sec, "damage")
        
        if not damage_raw:
            # Fallback to searching the whole file if turret_sec didn't have it
            damage_raw = get_tag_value(content, "damage")

        if damage_raw:
            # Split by whitespace and take the first number (Alpha Damage)
            parts = damage_raw.split()
            if parts:
                avg_damage = float(parts[0])

        # Calculate DPM: (60 / (Reload / Crew)) * Damage
        dpm = 0
        if reload_val > 0 and avg_damage > 0:
            eff_reload = reload_val / CREW_COEFF
            dpm = (60.0 / eff_reload) * avg_damage

        # --- MOBILITY CALCULATIONS ---
        eff_hull_traverse = (hull_traverse_base * CREW_COEFF) / hard_terrain
        eff_turret_traverse = turret_traverse_base * CREW_COEFF
        eff_mov = mov_factor / CREW_COEFF
        eff_rot = rot_factor / CREW_COEFF
        eff_tur_rot = turret_rot_factor / CREW_COEFF

        return {
            "name": os.path.splitext(os.path.basename(file_path))[0],
            "nation": nation,
            "tier": tier,
            "hp": hp,
            "tanks_gg_effective_stats": {
                "firepower": {
                    "damage_avg": avg_damage,
                    "reload_base": reload_val,
                    "dpm": round(dpm, 2),
                    "aim_time": aim,
                    "accuracy": acc
                },
                "mobility": {
                    "forward_speed": fw_speed,
                    "hull_traverse": round(eff_hull_traverse, 2),
                    "moving_bloom_max": round(eff_mov * fw_speed, 2),
                    "traverse_bloom_max": round(eff_rot * eff_hull_traverse, 2)
                },
                "gun_handling": {
                    "turret_traverse": round(eff_turret_traverse, 2),
                    "turret_bloom_max": round(eff_tur_rot * eff_turret_traverse, 2)
                }
            }
        }
    except Exception as e:
        # Useful for debugging if a specific tank fails
        # print(f"Error parsing {file_path}: {e}")
        return None

def main():
    if not os.path.exists(VEHICLES_FOLDER):
        print(f"❌ Folder not found: {VEHICLES_FOLDER}")
        print(f"Checking path: {os.path.abspath(VEHICLES_FOLDER)}")
        return

    all_tanks = []
    print(f"🚀 Scanning {VEHICLES_FOLDER}...")

    for root, _, files in os.walk(VEHICLES_FOLDER):
        # Determine nation based on folder name
        nation = os.path.basename(root)
        for file in files:
            if file.endswith(".xml") and not any(x in file for x in ["_cl.xml", "collision", "list.xml"]):
                data = parse_vehicle_file(os.path.join(root, file), nation)
                if data:
                    all_tanks.append(data)

    if not all_tanks:
        print("⚠️ No tanks found. JSON file was NOT updated.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_tanks, f, indent=4)
    
    print(f"✅ SUCCESS! Processed {len(all_tanks)} tanks into {OUTPUT_FILE}")

if __name__ == "__main__":
    main()