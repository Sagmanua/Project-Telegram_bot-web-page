import json

def merge_vehicle_stats(target_file, source_file, output_file):
    # Load the primary database (fixed_combined_db_with_images.json)
    with open(target_file, 'r', encoding='utf-8') as f:
        target_db = json.load(f)
    
    # Load the secondary database containing invisibility stats (full_vehicle_database2.json)
    with open(source_file, 'r', encoding='utf-8') as f:
        source_db = json.load(f)

    # Create a mapping of internal tags to invisibility stats for efficient lookup
    # Note: We convert to lowercase to ensure matching works even if casing differs
    invisibility_map = {}
    for vehicle in source_db:
        tag = vehicle.get("internal_name", "").lower()
        stats = vehicle.get("invisibility_stats")
        if tag and stats:
            invisibility_map[tag] = stats

    # Iterate through the target database and add the stats
    updated_count = 0
    for vehicle in target_db:
        # Use 'tag' field from the target DB to match with 'internal_name' from source DB
        # If 'tag' isn't available, we fallback to a normalized version of the 'name'
        vehicle_tag = vehicle.get("tag")
        if not vehicle_tag:
            # Fallback logic: replace spaces with underscores to try and match names
            vehicle_tag = vehicle.get("name", "").replace(" ", "_")
        
        lookup_key = vehicle_tag.lower()
        
        if lookup_key in invisibility_map:
            vehicle["invisibility_stats"] = invisibility_map[lookup_key]
            updated_count += 1

    # Save the updated database to a new file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(target_db, f, indent=4)
    
    print(f"Successfully updated {updated_count} vehicles with invisibility stats.")

# Run the merge
merge_vehicle_stats(
    'fixed_combined_db_with_images.json', 
    'full_vehicle_database2.json', 
    'merged_vehicle_database.json'
)