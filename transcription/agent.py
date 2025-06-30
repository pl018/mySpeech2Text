import os
import logging
import threading
import time
import datetime
import subprocess
import sys

from transcription.deepgram_client import DeepgramTranscriptionClient
from utils.logger import setup_session_logger
from config import LOG_DIR, TRANSCRIPT_DIR, SILENCE_LIMIT_SECONDS


class TranscriptionAgent:
    def __init__(self, gui):
        self.gui = gui
        self.is_running = False
        self.is_paused = False
        self.last_speech_time = 0
        self.stop_event = None
        self.transcription_thread = None
        self.silence_check_thread = None
        self.deepgram_client = None
        self.log_file_handler = None
        self.current_log_file = None
        self.current_transcript_file = None

        # Set up GUI callbacks
        self.gui.set_command_callbacks(
            toggle_func=self.toggle_start_stop,
            pause_func=self.toggle_pause,
            transcript_func=self.view_transcript,
            stop_func=self.stop,
        )

        # Initial UI update
        self.update_gui_state()

    def toggle_start_stop(self):
        """Toggle between starting and stopping transcription"""
        if self.is_running:
            self.stop()
        else:
            self.start()

    def toggle_pause(self):
        """Toggle between pausing and resuming transcription"""
        if not self.is_running:
            return

        self.is_paused = not self.is_paused
        logging.info(f"Transcription {'paused' if self.is_paused else 'resumed'}")

        # Update deepgram client pause state
        if self.deepgram_client:
            self.deepgram_client.pause(self.is_paused)

        self.update_gui_state()

    def start(self):
        """Start the transcription process"""
        if self.is_running:
            logging.warning("Transcription already running.")
            return

        # Setup logging and transcript files
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = os.path.join(LOG_DIR, f"session_{timestamp}.log")
        self.current_transcript_file = os.path.join(
            TRANSCRIPT_DIR, f"transcript_{timestamp}.txt"
        )
        self.log_file_handler = setup_session_logger(self.current_log_file)

        logging.info("=" * 20 + " Starting Transcription Session " + "=" * 20)
        self.is_running = True
        self.is_paused = False
        self.last_speech_time = time.time()
        self.stop_event = threading.Event()

        try:
            # Create deepgram client
            self.deepgram_client = DeepgramTranscriptionClient(
                on_speech_detected=self.on_speech_detected,
                on_speech_end=None,  # Not used currently
            )

            # Start transcription thread
            self.transcription_thread = threading.Thread(
                target=self._transcription_worker, daemon=True
            )
            self.transcription_thread.start()

            # Start silence checker thread
            self.silence_check_thread = threading.Thread(
                target=self._check_silence_loop, daemon=True
            )
            self.silence_check_thread.start()

        except Exception as e:
            logging.error(f"Failed to start transcription thread: {e}")
            self.is_running = False

        self.update_gui_state()

    def stop(self):
        """Stop the transcription process"""
        if not self.is_running:
            logging.warning("Transcription not running.")
            return

        logging.info("=" * 20 + " Stopping Transcription Session " + "=" * 20)
        if self.stop_event:
            self.stop_event.set()

        # Wait for threads to finish
        if self.transcription_thread and self.transcription_thread.is_alive():
            self.transcription_thread.join(timeout=5)
            if self.transcription_thread and self.transcription_thread.is_alive():
                logging.warning("Transcription thread did not terminate gracefully.")

        if self.silence_check_thread and self.silence_check_thread.is_alive():
            self.silence_check_thread.join(timeout=1)

        # Save transcript
        self._save_transcript()

        # Reset state
        self.is_running = False
        self.is_paused = False
        self.deepgram_client = None
        self.transcription_thread = None
        self.silence_check_thread = None
        self.stop_event = None

        # Close log file handler
        if self.log_file_handler:
            self.log_file_handler.close()
            logging.getLogger().removeHandler(self.log_file_handler)
            self.log_file_handler = None

        self.update_gui_state()

    def on_speech_detected(self):
        """Called when speech is detected to reset the silence timer"""
        self.last_speech_time = time.time()

    def view_transcript(self):
        """Open the current or last transcript file"""
        if self.current_transcript_file and os.path.exists(
            self.current_transcript_file
        ):
            try:
                logging.info(f"Opening transcript file: {self.current_transcript_file}")
                if sys.platform == "win32":
                    os.startfile(self.current_transcript_file)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", self.current_transcript_file])
                else:
                    subprocess.Popen(["xdg-open", self.current_transcript_file])
            except Exception as e:
                logging.error(f"Failed to open transcript file: {e}")
        else:
            logging.warning("No transcript available for the current/last session.")

    def update_gui_state(self):
        """Update the GUI state based on agent state"""
        self.gui.update_state(
            is_running=self.is_running,
            is_paused=self.is_paused,
            has_transcript_file=(
                self.current_transcript_file is not None
                and os.path.exists(self.current_transcript_file)
            ),
        )

    def _check_silence_loop(self):
        """Check for silence and auto-stop if silence threshold is reached"""
        while self.is_running and not self.stop_event.is_set():
            if not self.is_paused:
                silent_duration = time.time() - self.last_speech_time
                if silent_duration > SILENCE_LIMIT_SECONDS:
                    logging.info(
                        f"Silence limit ({SILENCE_LIMIT_SECONDS}s) reached. Auto-stopping."
                    )
                    # Schedule the stop call in the main GUI thread
                    self.gui.schedule_task(0, self.stop)
                    break
            time.sleep(1)

    def _transcription_worker(self):
        """Worker thread for handling transcription"""
        try:
            # Start deepgram client
            success = self.deepgram_client.start(self.stop_event)
            if not success:
                logging.error("Failed to start Deepgram client")
                self.gui.schedule_task(0, self.stop)
                return

            # Keep thread alive while running and connection is open
            while self.deepgram_client.is_connected() and not self.stop_event.is_set():
                time.sleep(0.1)

        except Exception as e:
            logging.exception(f"Fatal error in transcription worker: {e}")
        finally:
            # Clean up resources
            if self.deepgram_client:
                self.deepgram_client.stop()

            # Ensure stop is called if worker exits unexpectedly
            if self.is_running:
                logging.warning(
                    "Transcription worker exited unexpectedly. Stopping agent."
                )
                self.gui.schedule_task(0, self.stop)

    def _save_transcript(self):
        """Save the accumulated transcript to a file"""
        if not self.deepgram_client or not self.current_transcript_file:
            return

        session_transcript = self.deepgram_client.session_transcript

        if session_transcript:
            full_transcript = "\n".join(session_transcript).strip()
            if full_transcript:
                try:
                    with open(self.current_transcript_file, "w", encoding="utf-8") as f:
                        f.write(full_transcript)
                    logging.info(
                        f"Session transcript saved to: {self.current_transcript_file}"
                    )
                except Exception as e:
                    logging.error(f"Failed to save transcript: {e}")
            else:
                logging.info("No transcribed text to save for this session.")
        else:
            logging.info("No transcribed text to save for this session.")
