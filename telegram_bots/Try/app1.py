import os
import json
import re
import xml.etree.ElementTree as ET

# Update these paths to your actual local paths
VEHICLES_FOLDER = r"C:\Users\bestp\Desktop\Try\vehicles"
OUTPUT_FILE = "camo_database.json"

def find_tag_no_ns(element, tag_name):
    """Finds a tag regardless of XML namespace/prefix."""
    for el in element.iter():
        # Remove namespace from tag name (e.g., '{ns}maxHealth' -> 'maxHealth')
        clean_tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
        if clean_tag == tag_name:
            return el.text
    return None

def parse_vehicle_xml(file_path, nation):
    try:
        # Use 'replace' to handle potential encoding artifacts in game files
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            xml_content = f.read()

        # Basic cleanup: Remove the XML declaration if it's causing issues
        xml_content = re.sub(r'<\?xml.*\?>', '', xml_content)
        
        # Wrap in a try-block for ET parsing specifically
        try:
            root = ET.fromstring(f"<root>{xml_content}</root>")
        except ET.ParseError:
            return None

        # Extract data using the namespace-agnostic helper
        hp = find_tag_no_ns(root, "maxHealth")
        
        # If no HP is found, it might be a component file (like a gun) rather than a tank
        if not hp:
            return None

        tank_data = {
            "nation": nation,
            "internal_name": os.path.splitext(os.path.basename(file_path))[0],
            "name": find_tag_no_ns(root, "userString"),
            "tier": find_tag_no_ns(root, "level"),
            "type": find_tag_no_ns(root, "type"),
            "hp": hp,
            "view_range": find_tag_no_ns(root, "circularVisionRadius"),
            "camouflage": {
                "stationary": find_tag_no_ns(root, "stationary"),
                "moving": find_tag_no_ns(root, "moving"),
            }
        }

        return tank_data

    except Exception as e:
        # Uncomment for heavy debugging: print(f"Error parsing {file_path}: {e}")
        return None

def main():
    all_tanks = []

    if not os.path.exists(VEHICLES_FOLDER):
        print(f"❌ Error: Folder not found at {VEHICLES_FOLDER}")
        return

    # Use os.walk to search through all subfolders (nation/tank_name/etc)
    for root_dir, dirs, files in os.walk(VEHICLES_FOLDER):
        # Extract nation from path (assumes structure: vehicles/nation/...)
        parts = os.path.normpath(root_dir).split(os.sep)
        nation = parts[-1] if len(parts) > 0 else "unknown"

        for file in files:
            if file.endswith(".xml") and not file.endswith("_cl.xml"):
                file_path = os.path.join(root_dir, file)
                tank_data = parse_vehicle_xml(file_path, nation)

                if tank_data:
                    all_tanks.append(tank_data)
                    print(f"Found: {tank_data['internal_name']}")

    # Save output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_tanks, f, indent=4)

    print(f"\n✅ DONE! Saved {len(all_tanks)} tanks to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()