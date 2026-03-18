import os
import json
import re

# --- CONFIGURATION ---
BASE_DIR = r"C:\Project-Telegram_bot-web-page\Try"
VEHICLES_FOLDER = os.path.join(BASE_DIR, "vehicles")
OUTPUT_FILE = os.path.join(BASE_DIR, "full_vehicle_database.json")

CREW_COEFF = 1.043 

def clean_tank_name(raw_name):
    """
    Removes technical prefixes like 'ch01_', 'gb39_', 'R12_' and 
    formats the name to look like a normal tank name.
    """
    # 1. Remove nation prefixes (e.g., 'ch01_', 'gb101_', 'R12_')
    clean_name = re.sub(r'^[a-zA-Z]{1,2}\d+_+', '', raw_name)
    
    # 2. Format name
    clean_name = clean_name.replace('_', ' ').strip().title()
    
    # 3. Handle specific formatting for WZ and T series
    clean_name = re.sub(r'^Wz\s+', 'WZ-', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'^T\s+(\d)', r'T-\1', clean_name, flags=re.IGNORECASE)
    
    return clean_name

def find_tag_content(content, tag):
    if not content: return None
    pattern = rf"<{tag}(?:\s+[^>]*?)?>([\s\S]*?)</{tag}>"
    match = re.search(pattern, content)
    return match.group(1) if match else None

def get_clean_value(content, tag):
    raw = find_tag_content(content, tag)
    if raw:
        return re.sub(r'<.*?>', ' ', raw).strip()
    return None

def extract_number(text):
    if not text: return 0.0
    match = re.search(r"[-+]?\d*\.\d+|\d+", str(text))
    return float(match.group()) if match else 0.0

def parse_vehicle_file(file_path, nation):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if "<maxHealth>" not in content:
            return None

        # --- SECTION EXTRACTION ---
        chassis_sec = find_tag_content(content, "chassis") or ""
        turrets_sec = find_tag_content(content, "turrets0") or ""
        gun_sec = find_tag_content(turrets_sec, "guns") or find_tag_content(turrets_sec, "gun") or ""
        
        # --- DATA EXTRACTION ---
        hp = get_clean_value(content, "maxHealth")
        tier = get_clean_value(content, "level")
        fw_speed = extract_number(get_clean_value(content, "forward"))
        
        # Raw Chassis Stats (What you requested)
        hull_traverse_base = extract_number(get_clean_value(chassis_sec, "rotationSpeed"))
        mov_factor = extract_number(get_clean_value(chassis_sec, "vehicleMovement"))
        rot_factor = extract_number(get_clean_value(chassis_sec, "vehicleRotation"))
        
        # Terrain
        terrain_raw = get_clean_value(chassis_sec, "terrainResistance") or "1 1 2"
        hard_terrain = extract_number(terrain_raw.split()[0]) if terrain_raw else 1.0

        # Turret & Gun stats
        turret_traverse_base = extract_number(get_clean_value(turrets_sec, "rotationSpeed"))
        turret_rot_factor = extract_number(get_clean_value(turrets_sec, "turretRotation"))
        
        reload_val = extract_number(get_clean_value(gun_sec, "reloadTime") or get_clean_value(turrets_sec, "reloadTime"))
        aim = get_clean_value(gun_sec, "aimingTime") or get_clean_value(turrets_sec, "aimingTime")
        acc = get_clean_value(gun_sec, "shotDispersionRadius") or get_clean_value(turrets_sec, "shotDispersionRadius")
        damage_raw = get_clean_value(gun_sec, "damage") or get_clean_value(content, "damage")
        avg_damage = extract_number(damage_raw)

        # --- CALCULATIONS ---
        dpm = 0
        if reload_val > 0 and avg_damage > 0:
            eff_reload = reload_val / CREW_COEFF
            dpm = (60.0 / eff_reload) * avg_damage

        eff_hull_traverse = (hull_traverse_base * CREW_COEFF) / (hard_terrain if hard_terrain > 0 else 1.0)
        eff_turret_traverse = turret_traverse_base * CREW_COEFF
        
        raw_filename = os.path.splitext(os.path.basename(file_path))[0]

        return {
            "name": clean_tank_name(raw_filename),
            "nation": nation,
            "tier": tier,
            "hp": hp,
            # --- NEW SECTION ADDED HERE ---
            "chassis_stats": {
                "movement_dispersion": str(mov_factor),
                "rotation_dispersion": str(rot_factor),
                "traverse_speed": str(hull_traverse_base)
            },
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
                    "moving_bloom_max": round(mov_factor / CREW_COEFF * fw_speed, 2) if mov_factor else 0.0,
                    "traverse_bloom_max": round(rot_factor / CREW_COEFF * eff_hull_traverse, 2) if rot_factor else 0.0
                },
                "gun_handling": {
                    "turret_traverse": round(eff_turret_traverse, 2),
                    "turret_bloom_max": round(turret_rot_factor / CREW_COEFF * eff_turret_traverse, 2) if turret_rot_factor else 0.0
                }
            }
        }
    except Exception as e:
        return None

def main():
    if not os.path.exists(VEHICLES_FOLDER):
        print(f"❌ Folder not found: {VEHICLES_FOLDER}")
        return

    all_tanks = []
    for root, _, files in os.walk(VEHICLES_FOLDER):
        nation = os.path.basename(root)
        for file in files:
            if file.endswith(".xml") and not any(x in file.lower() for x in ["_cl.xml", "collision", "list.xml"]):
                data = parse_vehicle_file(os.path.join(root, file), nation)
                if data:
                    all_tanks.append(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_tanks, f, indent=4)
    
    print(f"✅ SUCCESS! Processed {len(all_tanks)} tanks.")

if __name__ == "__main__":
    main()