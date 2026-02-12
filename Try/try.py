import os
import json
import re

# --- CONFIGURATION ---
BASE_DIR = r"C:\Users\bestp\Desktop\Try"
VEHICLES_FOLDER = os.path.join(BASE_DIR, "vehicles")
OUTPUT_FILE = os.path.join(BASE_DIR, "full_vehicle_database.json")

# Tanks.gg Crew Constant (100% Crew + Commander Bonus is approx 1.043 factor)
CREW_COEFF = 1.043 

def get_tag_value(content, tag):
    """Finds the first occurrence of a tag and returns its text value."""
    pattern = rf"<{tag}>([\s\S]*?)</{tag}>"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else None

def parse_vehicle_file(file_path, nation):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if "<maxHealth>" not in content:
            return None

        # --- SECTION EXTRACTION ---
        # We grab the broad sections so we don't get lost in chassis/turret names
        chassis_sec = get_tag_value(content, "chassis") or ""
        turret_sec = get_tag_value(content, "turrets0") or ""
        
        # --- DATA EXTRACTION ---
        hp = get_tag_value(content, "maxHealth")
        tier = get_tag_value(content, "level")
        fw_speed = float(get_tag_value(content, "forward") or 0)
        
        # Chassis stats (Handling intermediate tags)
        hull_traverse_base = float(get_tag_value(chassis_sec, "rotationSpeed") or 0)
        terrain_raw = get_tag_value(chassis_sec, "terrainResistance") or "1 1 2"
        hard_terrain = float(terrain_raw.split()[0])
        
        mov_factor = float(get_tag_value(chassis_sec, "vehicleMovement") or 0)
        rot_factor = float(get_tag_value(chassis_sec, "vehicleRotation") or 0)

        # Turret & Gun stats
        turret_traverse_base = float(get_tag_value(turret_sec, "rotationSpeed") or 0)
        turret_rot_factor = float(get_tag_value(turret_sec, "turretRotation") or 0)
        
        reload = get_tag_value(turret_sec, "reloadTime")
        aim = get_tag_value(turret_sec, "aimingTime")
        acc = get_tag_value(turret_sec, "shotDispersionRadius")

        # --- TANKS.GG STYLE CALCULATIONS ---
        # 1. Effective Traverse: (Base * Crew) / Terrain
        eff_hull_traverse = (hull_traverse_base * CREW_COEFF) / hard_terrain
        eff_turret_traverse = turret_traverse_base * CREW_COEFF

        # 2. Effective Dispersion Factors: Base / Crew
        eff_mov = mov_factor / CREW_COEFF
        eff_rot = rot_factor / CREW_COEFF
        eff_tur_rot = turret_rot_factor / CREW_COEFF

        # 3. Bloom at Max Speed: Factor * Speed
        bloom_move = eff_mov * fw_speed
        bloom_hull = eff_rot * eff_hull_traverse
        bloom_turret = eff_tur_rot * eff_turret_traverse

        return {
            "name": os.path.splitext(os.path.basename(file_path))[0],
            "nation": nation,
            "tier": tier,
            "hp": hp,
            "tanks_gg_effective_stats": {
                "mobility": {
                    "forward_speed": fw_speed,
                    "hull_traverse": round(eff_hull_traverse, 2),
                    "moving_bloom_max": round(bloom_move, 2),
                    "traverse_bloom_max": round(bloom_hull, 2)
                },
                "gun_handling": {
                    "reload": reload,
                    "aim_time": aim,
                    "accuracy": acc,
                    "turret_traverse": round(eff_turret_traverse, 2),
                    "turret_bloom_max": round(bloom_turret, 2)
                }
            }
        }
    except Exception:
        return None

def main():
    if not os.path.exists(VEHICLES_FOLDER):
        print(f"❌ Folder not found: {VEHICLES_FOLDER}")
        return

    all_tanks = []
    print(f"🚀 Scanning {VEHICLES_FOLDER}...")

    for root, _, files in os.walk(VEHICLES_FOLDER):
        nation = os.path.normpath(root).split(os.sep)[-1]
        for file in files:
            if file.endswith(".xml") and not any(x in file for x in ["_cl.xml", "collision", "list.xml"]):
                data = parse_vehicle_file(os.path.join(root, file), nation)
                if data:
                    all_tanks.append(data)

    if not all_tanks:
        print("⚠️ No tanks found. JSON file was NOT updated to prevent data loss.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_tanks, f, indent=4)
    
    print(f"✅ SUCCESS! Processed {len(all_tanks)} tanks into {OUTPUT_FILE}")

if __name__ == "__main__":
    main()