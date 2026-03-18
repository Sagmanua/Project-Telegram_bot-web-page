
import requests

def get_tank_data(tank_name):
    app_id = "1c67a69b2758f598f6edab23ca7dbb7c"  # Replace with your Wargaming ID
    app_id = ""  # Replace with your Wargaming ID
    
    # 1. Get Tank ID and Basic Info from Wargaming
    wg_url = "https://api.worldoftanks.eu/wot/encyclopedia/vehicles/"
    wg_params = {"application_id": app_id, "fields": "name,tier,nation"}
    
    print(f"Searching for '{tank_name}'...")
    wg_data = requests.get(wg_url, params=wg_params).json()
    
    if wg_data["status"] != "ok":
        print("API Error. Check your App ID.")
        return

    # 2. Get Mastery Requirements from Tomato.gg
    # This public endpoint provides community-tracked MoE and Mastery data
    tomato_url = "https://api.tomato.gg/dev/api-v2/mastery/EU" # Change EU to NA if needed
    tomato_data = requests.get(tomato_url).json()
    
    # Mapping Tomato.gg data (they use tank_id as keys)
    mastery_map = {str(item['tank_id']): item for item in tomato_data['data']}

    found = False
    for t_id, info in wg_data["data"].items():
        if tank_name.lower() in info["name"].lower():
            print(f"\n--- {info['name']} ---")
            print(f"Tier: {info['tier']} | Nation: {info['nation'].upper()}")
            
            # Match Wargaming ID with Tomato.gg Mastery Data
            if t_id in mastery_map:
                m_info = mastery_map[t_id]
                print(f"Mastery Requirements (Base XP):")
                print(f"  - Ace Tanker (99%): {m_info['ace']} XP")
                print(f"  - 1st Class  (95%): {m_info['class1']} XP")
                print(f"  - 2nd Class  (80%): {m_info['class2']} XP")
                print(f"  - 3rd Class  (50%): {m_info['class3']} XP")
            else:
                print("Mastery data not available for this tank.")
            
            found = True
    
    if not found:
        print("No tank found with that name.")

if __name__ == "__main__":
    name = input("Enter tank name: ")
    get_tank_data(name)