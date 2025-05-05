import logging
import threading
import customtkinter as ctk
import time
import datetime
import os
import sys
import subprocess
from dotenv import load_dotenv
import keyboard
import pyautogui

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

# --- Configuration ---

load_dotenv()
HOTKEY = "ctrl+alt+\\"
SILENCE_LIMIT_SECONDS = 20
LOG_DIR = "logs"
TRANSCRIPT_DIR = "transcripts" # New directory for transcripts
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TRANSCRIPT_DIR, exist_ok=True) # Create transcript dir

# --- Global State ---
agent = None
_drag_data = {"x": 0, "y": 0} # For window dragging

# --- Logging Setup ---
def setup_session_logger(filename):
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    log_handler = logging.FileHandler(filename, mode='a') # Append mode
    log_handler.setFormatter(log_formatter)

    # Get root logger
    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicate logs if restarting
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        h.close() # Close the handler properly
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_handler)

    # Also log to console for debugging
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    return log_handler

# --- Transcription Agent Class ---
class TranscriptionAgent:
    def __init__(self, root_gui):
        self.root_gui = root_gui
        self.is_running = False
        self.is_paused = False
        self.last_speech_time = 0
        self.stop_event = None
        self.transcription_thread = None
        self.silence_check_thread = None
        self.dg_connection = None
        self.microphone = None
        self.is_finals = []
        self.session_transcript = [] # To store full transcript parts
        self.log_file_handler = None
        self.current_log_file = None
        self.current_transcript_file = None # Store path for saving

        self._setup_gui_controls()

        self.root_gui.bind("<ButtonPress-1>", self.on_drag_start)
        self.root_gui.bind("<ButtonRelease-1>", self.on_drag_stop)
        self.root_gui.bind("<B1-Motion>", self.on_drag_motion)

    def _setup_gui_controls(self):
        # Apply CustomTkinter settings
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Main frame covering the whole window (for background/dragging)
        main_frame = ctk.CTkFrame(self.root_gui, fg_color="transparent")
        main_frame.pack(fill=ctk.BOTH, expand=True)
        # --- Bind dragging events to the main frame as well ---
        main_frame.bind("<ButtonPress-1>", self.on_drag_start)
        main_frame.bind("<ButtonRelease-1>", self.on_drag_stop)
        main_frame.bind("<B1-Motion>", self.on_drag_motion)

        # --- Top "Title Bar" Area ---
        top_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        top_frame.pack(fill=ctk.X, padx=5, pady=(2, 0))
        # --- Bind dragging events to the top frame too ---
        top_frame.bind("<ButtonPress-1>", self.on_drag_start)
        top_frame.bind("<ButtonRelease-1>", self.on_drag_stop)
        top_frame.bind("<B1-Motion>", self.on_drag_motion)

        # Status Label (Top Left)
        self.status_label = ctk.CTkLabel(top_frame, text="Idle", text_color="gray", anchor="w")
        self.status_label.pack(side=ctk.LEFT, padx=(3, 0))
        # --- Bind dragging events ---
        self.status_label.bind("<ButtonPress-1>", self.on_drag_start)
        self.status_label.bind("<ButtonRelease-1>", self.on_drag_stop)
        self.status_label.bind("<B1-Motion>", self.on_drag_motion)

        # Transcript Button (Top Right) - Unicode: 📄 U+1F4C4
        icon_font_small = ctk.CTkFont(size=20)
        self.transcript_button = ctk.CTkButton(
            top_frame,
            text="📄",
            width=25,
            height=25,
            font=icon_font_small,
            text_color="white",
            fg_color="transparent",
            hover=False,
            command=self.view_transcript,
        )
        self.transcript_button.pack(side=ctk.RIGHT, padx=(0, 3))

        # --- Bottom Control Buttons Area ---
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill=ctk.X, pady=(0, 5))
        # Three equal columns: Pause | Record | Reset
        for i in range(3):
            button_frame.columnconfigure(i, weight=1)

        # --- Bind dragging events for button frame ---
        button_frame.bind("<ButtonPress-1>", self.on_drag_start)
        button_frame.bind("<ButtonRelease-1>", self.on_drag_stop)
        button_frame.bind("<B1-Motion>", self.on_drag_motion)

        icon_font_large = ctk.CTkFont(size=32)  # Larger icons for main controls

        # Pause / Resume Button (left)
        # Unicode: ⏸️ pause, ▶️ play
        self.pause_resume_button = ctk.CTkButton(
            button_frame,
            text="⏸️",
            width=40,
            height=40,
            font=icon_font_large,
            text_color="white",
            fg_color="transparent",
            hover=False,
            command=self.toggle_pause,
            state=ctk.DISABLED,
        )
        self.pause_resume_button.grid(row=0, column=0, padx=5)

        # Record / Stop Button (center)
        # Unicode: 🎤 mic for record, ⏹️ for stop
        self.record_button = ctk.CTkButton(
            button_frame,
            text="🎤",
            width=40,
            height=40,
            font=icon_font_large,
            text_color="red",
            fg_color="transparent",
            hover=False,
            command=self.toggle_start_stop,
        )
        self.record_button.grid(row=0, column=1, padx=5)

        # Reset Button (right) – Unicode: 🔄 U+1F504
        self.reset_button = ctk.CTkButton(
            button_frame,
            text="🔄",
            width=40,
            height=40,
            font=icon_font_large,
            text_color="white",
            fg_color="transparent",
            hover=False,
            command=self.reset_interface,
            state=ctk.DISABLED,
        )
        self.reset_button.grid(row=0, column=2, padx=5)

    def _update_gui_state(self):
        # Determine icon/text/color based on state
        if self.is_running:
            record_icon = "🎤"  # Mic icon when running
            record_color = "red"
            pause_icon = "⏸️" if self.is_paused else "⏸️"
            pause_color = "green" if self.is_paused else "white"
            pause_state = ctk.NORMAL
            record_state = ctk.NORMAL
            reset_state = ctk.NORMAL
            transcript_state = ctk.DISABLED  # Will enable when not running but transcript exists
            if self.is_paused:
                status_text = "Paused"
                status_color = "orange"
            else:
                status_text = "Running"
                status_color = "green"
        else:
            record_icon = "🎤"  # Mic icon when idle
            record_color = "red"
            pause_icon = "⏸️"  # Pause icon (disabled)
            pause_color = "gray"
            pause_state = ctk.DISABLED
            record_state = ctk.NORMAL  # Always allow starting
            reset_state = ctk.DISABLED
            transcript_state = ctk.NORMAL if self.current_transcript_file else ctk.DISABLED
            status_text = "Idle"
            status_color = "gray"

        # Update GUI elements
        self.status_label.configure(text=status_text, text_color=status_color)
        self.record_button.configure(text=record_icon, text_color=record_color, state=record_state)
        self.pause_resume_button.configure(text=pause_icon, text_color=pause_color, state=pause_state)
        self.reset_button.configure(state=reset_state)
        self.transcript_button.configure(state=transcript_state)

        # Close log file handle if becoming idle
        if not self.is_running and self.log_file_handler:
            self.log_file_handler.close()
            logging.getLogger().removeHandler(self.log_file_handler)
            self.log_file_handler = None

    def toggle_start_stop(self):
        if self.is_running:
            self.stop()
        else:
            self.start()

    def toggle_pause(self):
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        logging.info(f"Transcription {'paused' if self.is_paused else 'resumed'}")
        self._update_gui_state()

    def start(self):
        if self.is_running:
            logging.warning("Transcription already running.")
            return

        # Setup Logging and Transcript for new session
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = os.path.join(LOG_DIR, f"session_{timestamp}.log")
        self.current_transcript_file = os.path.join(TRANSCRIPT_DIR, f"transcript_{timestamp}.txt")
        self.log_file_handler = setup_session_logger(self.current_log_file)
        self.session_transcript = [] # Reset transcript buffer

        logging.info("="*20 + " Starting Transcription Session " + "="*20)
        self.is_running = True
        self.is_paused = False
        self.last_speech_time = time.time() # Reset silence timer
        self.stop_event = threading.Event()
        self.is_finals = []

        try:
            # Start Deepgram connection and microphone in a separate thread
            self.transcription_thread = threading.Thread(target=self._transcription_worker, daemon=True)
            self.transcription_thread.start()

            # Start silence checker thread
            self.silence_check_thread = threading.Thread(target=self._check_silence_loop, daemon=True)
            self.silence_check_thread.start()

        except Exception as e:
            logging.error(f"Failed to start transcription thread: {e}")
            self.is_running = False # Ensure state is correct on failure

        self._update_gui_state()

    def stop(self):
        if not self.is_running:
            logging.warning("Transcription not running.")
            return

        logging.info("="*20 + " Stopping Transcription Session " + "="*20)
        if self.stop_event:
            self.stop_event.set()

        # Wait for threads to finish
        if self.transcription_thread and self.transcription_thread.is_alive():
            self.transcription_thread.join(timeout=5)
            if self.transcription_thread.is_alive():
                 logging.warning("Transcription thread did not terminate gracefully.")
        if self.silence_check_thread and self.silence_check_thread.is_alive():
             self.silence_check_thread.join(timeout=1)

        # --- Save Transcript ---
        if self.session_transcript and self.current_transcript_file:
            full_transcript = "\n".join(self.session_transcript).strip() # Join lines
            if full_transcript: # Only save if there's content
                try:
                    with open(self.current_transcript_file, 'w', encoding='utf-8') as f:
                        f.write(full_transcript)
                    logging.info(f"Session transcript saved to: {self.current_transcript_file}")
                except Exception as e:
                    logging.error(f"Failed to save transcript: {e}")
            else:
                logging.info("No transcribed text to save for this session.")
        # --- End Save Transcript ---

        self.is_running = False
        self.is_paused = False
        self.dg_connection = None # Ensure resources are released
        self.microphone = None
        self.transcription_thread = None
        self.silence_check_thread = None
        self.stop_event = None
        # self.current_transcript_file is retained for View Transcript button

        self._update_gui_state() # Update GUI last

    def _check_silence_loop(self):
        while self.is_running and not self.stop_event.is_set():
            if not self.is_paused:
                silent_duration = time.time() - self.last_speech_time
                if silent_duration > SILENCE_LIMIT_SECONDS:
                    logging.info(f"Silence limit ({SILENCE_LIMIT_SECONDS}s) reached. Auto-stopping.")
                    # Schedule the stop call in the main GUI thread to avoid Tkinter issues
                    self.root_gui.after(0, self.stop)
                    break # Exit loop once stop is initiated
            time.sleep(1) # Check every second

    def view_transcript(self):
        """Open the most recently created transcript for the current or last session."""
        if self.current_transcript_file and os.path.exists(self.current_transcript_file):
            try:
                logging.info(f"Opening transcript: {self.current_transcript_file}")
                if sys.platform == "win32":
                    os.startfile(self.current_transcript_file)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", self.current_transcript_file])
                else:
                    subprocess.Popen(["xdg-open", self.current_transcript_file])
            except Exception as e:
                logging.error(f"Failed to open transcript file: {e}")
        else:
            logging.warning("No transcript available yet.")

    def reset_interface(self):
        """Fully reset to idle state, discarding any ongoing session without saving."""
        if self.is_running:
            self.stop()
        # Additional UI reset if needed
        self._update_gui_state()

    def _transcription_worker(self):
        try:
            deepgram: DeepgramClient = DeepgramClient()
            self.dg_connection = deepgram.listen.websocket.v("1")

            def on_open(connection, open_event, **kwargs):
                logging.info("Deepgram Connection Open")

            def on_message(connection, result, **kwargs):
                if self.is_paused: return # Ignore messages if paused

                try:
                    sentence = result.channel.alternatives[0].transcript
                    if len(sentence) > 0:
                        self.last_speech_time = time.time() # Update on any transcript

                    if result.is_final:
                        self.is_finals.append(sentence)
                        if result.speech_final:
                            utterance = " ".join(self.is_finals).strip()
                            if utterance:
                                logging.info(f"Typing (Speech Final): {utterance}")
                                pyautogui.typewrite(utterance + ' ', interval=0.01)
                                self.session_transcript.append(utterance) # Add to transcript
                                self.is_finals = []
                        # We type only on speech_final now for better sentence structure
                        # else:
                        #     # Optionally type interim 'is_final' results if needed sooner
                        #     interim_final = self.is_finals[-1]
                        #     logging.info(f"Typing (Is Final): {interim_final}")
                        #     pyautogui.typewrite(interim_final + ' ', interval=0.01)

                    # else: # Interim results (optional logging/display)
                    #    logging.debug(f"Interim: {sentence}")

                except Exception as e:
                    logging.error(f"Error processing message: {e} - Data: {result}")

            def on_utterance_end(connection, utterance_end, **kwargs):
                 # UtteranceEnd can sometimes help finalize phrases sooner than speech_final
                 if self.is_paused: return
                 if self.is_finals:
                    utterance = " ".join(self.is_finals).strip()
                    if utterance:
                       logging.info(f"Typing (Utterance End): {utterance}")
                       pyautogui.typewrite(utterance + ' ', interval=0.01)
                       self.session_transcript.append(utterance) # Add to transcript
                    self.is_finals = []
                    self.last_speech_time = time.time()
                 logging.debug("Utterance End received")


            def on_speech_started(connection, speech_started, **kwargs):
                if self.is_paused: return
                logging.debug("Speech Started")
                self.last_speech_time = time.time() # Reset silence timer on speech start

            def on_metadata(connection, metadata, **kwargs):
                logging.debug(f"Metadata: {metadata}")

            def on_close(connection, close, **kwargs):
                logging.info(f"Deepgram Connection Closed: {close}")

            def on_error(connection, error, **kwargs):
                logging.error(f"Deepgram Error: {error}")

            def on_unhandled(connection, unhandled, **kwargs):
                logging.warning(f"Unhandled Websocket Message: {unhandled}")


            self.dg_connection.on(LiveTranscriptionEvents.Open, on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
            self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Unhandled, on_unhandled)

            options = LiveOptions(
                model="nova-3", # Or your preferred model
                language="en-US",
                smart_format=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
                interim_results=True, # Keep true for faster feedback if needed
                utterance_end_ms="1000",
                vad_events=True,
                endpointing=300, # Lower latency endpointing
            )
            addons = {"no_delay": "true"}

            logging.info("Starting Deepgram connection...")
            if self.dg_connection.start(options, addons=addons) is False:
                logging.error("Failed to connect to Deepgram")
                self.root_gui.after(0, self.stop) # Ensure stop is called from GUI thread
                return

            self.microphone = Microphone(self.dg_connection.send)
            self.microphone.start()
            logging.info("Microphone started")

            # Keep thread alive while running and connection is open
            while self.dg_connection.is_connected() and not self.stop_event.is_set():
                 time.sleep(0.1) # Keep thread responsive

        except Exception as e:
            logging.exception(f"Fatal error in transcription worker: {e}")
        finally:
            if self.microphone:
                self.microphone.finish()
                logging.info("Microphone finished.")
            if self.dg_connection:
                self.dg_connection.finish()
                logging.info("Deepgram connection finished.")
            # Ensure stop is called if worker exits unexpectedly
            if self.is_running:
                 logging.warning("Transcription worker exited unexpectedly. Stopping agent.")
                 self.root_gui.after(0, self.stop)

    # --- Window Dragging Methods ---
    def on_drag_start(self, event):
        global _drag_data
        _drag_data["x"] = event.x
        _drag_data["y"] = event.y

    def on_drag_stop(self, event):
        global _drag_data
        _drag_data["x"] = 0
        _drag_data["y"] = 0

    def on_drag_motion(self, event):
        global _drag_data
        # calculate x and y coordinates of mouse cursor
        x = self.root_gui.winfo_pointerx() - _drag_data["x"]
        y = self.root_gui.winfo_pointery() - _drag_data["y"]
        self.root_gui.geometry(f"+{x}+{y}")
    # --- End Window Dragging ---


# --- Main Application Setup ---
def main():
    global agent

    # Use CTk for the root window
    root = ctk.CTk()
    root.title("Transcription Agent") # Title won't be visible
    root.geometry("150x90") # Adjusted size
    root.resizable(False, False)
    root.wm_attributes("-topmost", True) # Always on top

    # --- Make window borderless --- Needs to be after initial geometry?
    root.overrideredirect(1)

    # --- Transparency ---
    try:
        # Try setting transparency *after* overrideredirect
        root.attributes("-alpha", 0.75)
    except ctk.TclError:
        logging.warning("Window transparency not supported on this system.")


    agent = TranscriptionAgent(root)

    # Hotkey setup
    try:
        keyboard.add_hotkey(HOTKEY, agent.toggle_start_stop)
        logging.info(f"Hotkey '{HOTKEY}' registered. Press it to toggle transcription.")
    except Exception as e:
        logging.error(f"Failed to register hotkey '{HOTKEY}'. Maybe run with sudo/admin privileges? Error: {e}")


    # Graceful shutdown
    def on_closing():
        logging.info("GUI closing. Stopping agent...")
        if agent:
            agent.stop()
        keyboard.remove_all_hotkeys() # Clean up hotkeys
        root.destroy()

    # Since there's no WM_DELETE_WINDOW, maybe bind Escape key or add a quit button if needed
    # root.protocol("WM_DELETE_WINDOW", on_closing) # This won't work with overrideredirect
    # Optional: Bind Escape key to close
    root.bind("<Escape>", lambda e: on_closing())
    logging.info("Press Esc key while the agent window is focused to close.")


    agent._update_gui_state() # Set initial GUI state
    root.mainloop()

if __name__ == "__main__":
    main()