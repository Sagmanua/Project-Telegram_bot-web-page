import os
from PIL import Image
try:
    import imagecodecs
except ImportError:
    print("Error: 'imagecodecs' not found. Run: pip install imagecodecs")

def convert_dds_to_png(source_path):
    """
    Converts a DDS file to PNG. 
    Handles single files or directories.
    """
    # Check if path is a directory
    if os.path.isdir(source_path):
        files = [os.path.join(source_path, f) for f in os.listdir(source_path) if f.lower().endswith('.dds')]
    else:
        files = [source_path]

    if not files:
        print("No .dds files found.")
        return

    for file_path in files:
        try:
            with Image.open(file_path) as img:
                # 1. Ensure we are in RGBA mode to keep transparency/alpha channels
                img = img.convert("RGBA")
                
                # 2. Fix orientation (DDS is often stored 'upside down' compared to PNG)
                # If your images look correct, you can comment out the next line.
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
                
                # 3. Create output filename
                target_path = os.path.splitext(file_path)[0] + ".png"
                
                # 4. Save
                img.save(target_path, "PNG")
                print(f"✅ Converted: {os.path.basename(file_path)} -> {os.path.basename(target_path)}")
                
        except Exception as e:
            print(f"❌ Failed to convert {file_path}: {e}")

if __name__ == "__main__":
    # CHANGE THIS to your filename or folder path
    path_to_convert = "mmap.dds" 
    
    if os.path.exists(path_to_convert):
        convert_dds_to_png(path_to_convert)
    else:
        print(f"File or folder '{path_to_convert}' not found.")