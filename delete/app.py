import json

# Replace 'tanks.json' with your actual filename
input_filename = 'tanks_data.json'
output_filename = 'tanks_updated.json'

try:
    # 1. Load the data from your JSON file
    with open(input_filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. Iterate through the list and remove 'date'
    # This handles both a single dictionary or a list of dictionaries
    if isinstance(data, list):
        for entry in data:
            if "date" in entry:
                del entry["date"]
    elif isinstance(data, dict):
        if "date" in data:
            del data["date"]

    # 3. Save the modified data to a new file
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Success! Updated data saved to {output_filename}")

except FileNotFoundError:
    print(f"Error: The file '{input_filename}' was not found.")
except json.JSONDecodeError:
    print("Error: Failed to decode JSON. Check if your file format is valid.")