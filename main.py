import logging
import keyboard
import sys

from ui.gui import TranscriptionGUI
from transcription.agent import TranscriptionAgent
from config import HOTKEY, UI_WIDTH, UI_HEIGHT, UI_OPACITY

def main():
    # Initialize GUI
    gui = TranscriptionGUI(UI_WIDTH, UI_HEIGHT, UI_OPACITY)
    
    # Create transcription agent
    agent = TranscriptionAgent(gui)
    
    # Register hotkey
    try:
        keyboard.add_hotkey(HOTKEY, agent.toggle_start_stop)
        logging.info(f"Hotkey '{HOTKEY}' registered. Press it to toggle transcription.")
    except Exception as e:
        logging.error(f"Failed to register hotkey '{HOTKEY}'. Maybe run with sudo/admin privileges? Error: {e}")
    
    # Set up graceful shutdown
    def on_closing():
        logging.info("GUI closing. Stopping agent...")
        agent.stop()
        keyboard.remove_all_hotkeys()  # Clean up hotkeys
        gui.root.destroy()
    
    # Register escape key to close
    gui.add_escape_handler(on_closing)
    logging.info("Press Esc key while the agent window is focused to close.")
    
    # Start GUI main loop
    gui.start()

if __name__ == "__main__":
    main()