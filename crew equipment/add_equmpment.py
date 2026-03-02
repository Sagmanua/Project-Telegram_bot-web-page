import json
import random

# List of equipment images provided
EQUIPMENT_LIST = [
    "dosel.png", "gryntu.png", "komandirsky_priboru.png", "komponovka.png", 
    "maloshumka.png", "mask_seti.png", "mehanism_povoroto.png", "optika.png", 
    "podboi.png", "pricel.png", "privodu.png", "stab.png", "t3_pricel.png", 
    "t3_stab.png", "t3_tyrbuna.png", "t3_zakalka.png", "trybu.png", 
    "turbina.png", "ventil.png", "zakalka.png"
]

def update_tanks_with_random_equipment(file_path):
    try:
        # Load the existing tank data
        with open(file_path, 'r', encoding='utf-8') as f:
            tanks_data = json.load(f)

        # Process each tank entry
        for i, tank in enumerate(tanks_data):
            # Skip the first entry if it's just the header/template
            if tank.get("tank_name") == "Tank Name":
                continue
            
            # Randomly select 3 unique equipment images for each tank
            # 'random.sample' ensures the same image cannot be picked twice for one tank
            random_equipment = random.sample(EQUIPMENT_LIST, 3)
            
            # Add the selected images to the tank object
            tank["equipment"] = random_equipment

        # Save the updated data back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tanks_data, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully updated {len(tanks_data) - 1} tanks with random equipment.")

    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the script
update_tanks_with_random_equipment('tanks_data.json')