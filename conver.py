import csv
import json
from datetime import datetime

def convert_tank_csv_to_json(input_file, output_file):
    tank_list = []
    current_date = "2026-02-25"

    # Your custom labels in the correct order for the numerical data
    labels = [
        "Tank DPM", "Dmg", "Reload", "Pen", "Velo", 
        "Acc", "Aim", "Dispresion", "DeP/Elev", "Speed", 
        "Traverse", "Power", "P/W", "Weight", "Health", "VR"
    ]

    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or len(row) < 5: continue
                
                # Logic to align with your specific CSV structure:
                # row[0] = T-34 (Name)
                # row[3] = VII (Tier)
                # row[4] = T-34-2G FT (Full Name)
                # Numerical data starts at row[6]
                
                tank_obj = {
                    "date": current_date,
                    "tank_name": row[0],
                    "tier": row[3],
                    "full_name": row[4]
                }
                
                # Start mapping your 16 custom labels from index 6 of the CSV row
                for i, label in enumerate(labels):
                    try:
                        val = row[i + 6].strip()
                        tank_obj[label] = val if val != "" else None
                    except IndexError:
                        tank_obj[label] = None
                
                tank_list.append(tank_obj)

        with open(output_file, mode='w', encoding='utf-8') as out_f:
            json.dump(tank_list, out_f, indent=4, ensure_ascii=False)
            
        print(f"Success! Processed {len(tank_list)} tanks.")

    except FileNotFoundError:
        print(f"Error: {input_file} not found.")

convert_tank_csv_to_json('tanks.csv', 'tanks_data.json')