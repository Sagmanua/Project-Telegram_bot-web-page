import json

# Load the JSON file
with open("tanks_with_ids.json", "r", encoding="utf-8") as f:
    tanks_data = json.load(f)

# Collect names of tanks missing 'tank_id'
missing_id_tanks = [tank["full_name"] for tank in tanks_data if "tank_id" not in tank]

# Print the results
if missing_id_tanks:
    print("Tanks without 'tank_id':")
    for name in missing_id_tanks:
        print("-", name)
else:
    print("All tanks have 'tank_id'.")