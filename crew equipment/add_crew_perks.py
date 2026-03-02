import json
import random

def update_tanks_with_crew(file_path):
    # Perks available to all crew members
    all_perks = ["bratstvo.png", "maskirovka.png", "remka.png"]
    
    # Perks specific to each role
    specific_perks = {
        "comander": [
            "Coordination.png", "Emergency.png", "mentor.png", 
            "Practicality.png", "Recon.png", "Sound Detection.png"
        ],
        "driver": [
            "Clutch_Braking.png", "Controlled_Impact.png", "Engineer.png", 
            "Off-Road_Driving.png", "Reliable_Placement.png", "Smooth_Ride.png"
        ],
        "gunner": [
            "Armorer.png", "Concentration.png", "Deadeye.png", 
            "Designated_Target.png", "Quick_Aiming.png", "Snap_Shot.png"
        ],
        "loader": [
            "Adrenaline_Rush.png", "Ammo_Tuning.png", "Close_Combat.png", 
            "Intuition.png", "Perfect_Charge.png", "Safe_Stowage.png"
        ],
        "radist": [
            "Communications_Expert.png", "Firefighting.png", "Jamming.png", 
            "Side_by_Side.png", "Signal_Interception.png", "Situational_Awareness.png"
        ]
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tanks_data = json.load(f)

        for tank in tanks_data:
            # Skip the template/header row
            if tank.get("tank_name") == "Tank Name":
                continue
                
            crew = {}
            for member, perks in specific_perks.items():
                # Randomly pick 3 unique perks from the role-specific folder
                selected_specific = random.sample(perks, 3)
                
                # Construct the full list of 6 perks
                # 3 from 'all' folder + 3 from the specific folder
                combined_perks = []
                for p in all_perks:
                    combined_perks.append(f"images_perks/all/{p}")
                for p in selected_specific:
                    combined_perks.append(f"images_perks/{member}/{p}")
                
                crew[member] = combined_perks
            
            # Add the crew object to the tank
            tank["crew"] = crew

        # Save the updated data back to the JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(tanks_data, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully updated {len(tanks_data)-1} tanks with crew data.")

    except Exception as e:
        print(f"Error: {str(e)}")

# Run the update
update_tanks_with_crew('tanks_data.json')