import os

# Let's peek at just ONE file to see why it's failing
VEHICLES_FOLDER = r"C:\Users\bestp\Desktop\Try\vehicles"

def diagnose():
    for root_dir, dirs, files in os.walk(VEHICLES_FOLDER):
        for file in files:
            if file.endswith(".xml"):
                path = os.path.join(root_dir, file)
                print(f"--- Checking File: {file} ---")
                try:
                    with open(path, 'r', errors='ignore') as f:
                        lines = f.readlines()[:10] # Read first 10 lines
                        print("".join(lines))
                except:
                    print("Could not even open file.")
                return # Stop after one file

diagnose()