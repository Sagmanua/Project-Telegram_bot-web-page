import json
import re

def normalize_name(name):
    """Normalizes tank names to improve matching (e.g., 'IS-2' -> 'is2')."""
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def fix_and_merge(full_db_path, api_db_path, output_path):
    with open(full_db_path, 'r', encoding='utf-8') as f:
        full_db = json.load(f)
    with open(api_db_path, 'r', encoding='utf-8') as f:
        api_db = json.load(f)

    # Create a lookup map using normalized names
    api_map = {normalize_name(item['name']): item for item in api_db}
    
    combined_data = []

    for vehicle in full_db:
        # 1. Standardize Tier to integer
        if 'tier' in vehicle:
            vehicle['tier'] = int(vehicle['tier'])
            
        norm_name = normalize_name(vehicle['name'])
        
        if norm_name in api_map:
            api_data = api_map[norm_name]
            
            # 2. Merge API metadata (ID, Tag)
            vehicle['api_id'] = api_data.get('api_id')
            vehicle['tag'] = api_data.get('tag')
            
            # 3. Fix the "Zero Stats" issue
            # We take the high-quality damage/dpm from the API file
            api_stats = api_data.get('stats', {})
            tanks_gg_firepower = vehicle.get('tanks_gg_effective_stats', {}).get('firepower', {})
            
            # Update the placeholders with real data
            tanks_gg_firepower['damage_avg'] = api_stats.get('damage_avg', 0)
            tanks_gg_firepower['dpm'] = api_stats.get('dpm', 0)
            
            # Keep the rest of the technical stats (reload, accuracy, etc.)
        
        combined_data.append(vehicle)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=4)

fix_and_merge('full_vehicle_database.json', 'wot_api_database.json', 'fixed_combined_db.json')