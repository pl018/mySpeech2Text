import os
from dotenv import load_dotenv

load_dotenv()

# Application Configuration
HOTKEY = "ctrl+alt+\\"
SILENCE_LIMIT_SECONDS = 20

# Directory Configuration
LOG_DIR = "logs"
TRANSCRIPT_DIR = "transcripts"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

# UI Configuration
UI_WIDTH = 150
UI_HEIGHT = 70
UI_OPACITY = 0.75

# Button Configuration
BTN_RECORD_ICON = "🔴"
BTN_STOP_ICON = "⬜"
BTN_PAUSE_ICON = "⏯"
BTN_PLAY_ICON = "⏯"
BTN_TRANSCRIPT_ICON = "📄"

# Button Sizes
BTN_RECORD_SIZE = 30

BTN_CONTROL_SIZE = 20

# Button Colors
BTN_RECORD_COLOR = "#FF9999"
BTN_RECORD_ACTIVE_COLOR = "#FF0000"
BTN_CONTROL_COLOR = "white"
BTN_DISABLED_COLOR = "gray"
BTN_PAUSED_COLOR = "green"

# Deepgram Configuration
DG_MODEL = "nova-3"
DG_LANGUAGE = "en-US"
DG_SAMPLE_RATE = 16000
DG_UTTERANCE_END_MS = "1000"
DG_ENDPOINTING = 300