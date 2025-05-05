import os
from PIL import Image

def convert_png_to_ico(png_path, output_path=None):
    """
    Convert PNG image to ICO format suitable for Windows applications.
    
    Args:
        png_path (str): Path to the PNG file
        output_path (str, optional): Path for the output ICO file. If None, 
                                     will use the same name with .ico extension.
    
    Returns:
        str: Path to the generated ICO file
    """
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG file not found: {png_path}")
    
    # If no output path provided, create one
    if output_path is None:
        output_dir = os.path.dirname(png_path)
        base_name = os.path.splitext(os.path.basename(png_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}.ico")
    
    # Convert to ICO format
    try:
        img = Image.open(png_path)
        
        # Create icon in multiple sizes
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
        img.save(output_path, sizes=sizes)
        
        print(f"Successfully converted {png_path} to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error converting icon: {e}")
        return None
        
if __name__ == "__main__":
    # Can be run directly to test
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    png_path = os.path.join(script_dir, "mic.png")
    convert_png_to_ico(png_path) 