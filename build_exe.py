import os
import subprocess
import sys
import shutil

def build_exe():
    """
    Builds a single-file executable for the Speech-to-Text application.
    """
    print("Starting build process for Speech-to-Text App...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully.")
    
    # Create necessary directories if they don't exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("transcripts", exist_ok=True)
    
    # Use the existing ICO file directly
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "mic.ico")
    
    if os.path.exists(icon_path):
        print(f"Found icon file at: {icon_path}")
    else:
        print(f"Warning: Icon file not found at {icon_path}, using default icon")
        icon_path = "NONE"
    
    # Build the executable
    print("Building executable (this may take a few minutes)...")
    
    pyinstaller_command = [
        "pyinstaller",
        "--onefile",                # Single file output
        "--windowed",               # No console window
        "--name=SpeechToText",      # Name of the output executable
        f"--icon={icon_path}",      # Use the ICO file directly
        "--add-data=.env;.",        # Include .env file
        # Include both icon files as resources
        f"--add-data={icon_path};.", 
        "--hidden-import=keyboard", # Include hidden imports
        "--hidden-import=pyautogui",
        "--hidden-import=customtkinter",
        "--hidden-import=deepgram",
        "--clean",                  # Clean PyInstaller cache
        "main.py"                   # Entry point
    ]
    
    subprocess.check_call(pyinstaller_command)
    
    print("\nBuild completed!")
    print("The executable is located in the 'dist' folder.")
    print("Make sure the logs/ and transcripts/ folders are in the same directory as the executable.")
    
if __name__ == "__main__":
    build_exe() 