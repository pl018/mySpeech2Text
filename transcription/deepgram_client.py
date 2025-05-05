import logging
import time
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)
import pyautogui
from config import DG_MODEL, DG_LANGUAGE, DG_SAMPLE_RATE, DG_UTTERANCE_END_MS, DG_ENDPOINTING

class DeepgramTranscriptionClient:
    def __init__(self, on_speech_detected, on_speech_end):
        self.is_paused = False
        self.is_finals = []
        self.session_transcript = []
        self.connection = None
        self.microphone = None
        self.stop_event = None
        self.on_speech_detected = on_speech_detected
        self.on_speech_end = on_speech_end
    
    def start(self, stop_event):
        """Start the Deepgram transcription"""
        try:
            self.stop_event = stop_event
            deepgram = DeepgramClient()
            self.connection = deepgram.listen.websocket.v("1")
            
            # Set up event handlers
            self._setup_event_handlers()
            
            # Configure options
            options = self._get_transcription_options()
            addons = {"no_delay": "true"}
            
            # Start connection
            logging.info("Starting Deepgram connection...")
            if self.connection.start(options, addons=addons) is False:
                logging.error("Failed to connect to Deepgram")
                return False
            
            # Start microphone
            self.microphone = Microphone(self.connection.send)
            self.microphone.start()
            logging.info("Microphone started")
            return True
            
        except Exception as e:
            logging.exception(f"Error starting Deepgram transcription: {e}")
            return False
    
    def pause(self, is_paused):
        """Set pause state"""
        self.is_paused = is_paused
    
    def stop(self):
        """Stop transcription and clean up resources"""
        if self.microphone:
            self.microphone.finish()
            logging.info("Microphone finished.")
        
        if self.connection:
            self.connection.finish()
            logging.info("Deepgram connection finished.")
        
        self.connection = None
        self.microphone = None
        
        return self.session_transcript
    
    def is_connected(self):
        """Check if connection is active"""
        return self.connection and self.connection.is_connected()
    
    def _get_transcription_options(self):
        """Get Deepgram transcription options"""
        return LiveOptions(
            model=DG_MODEL,
            language=DG_LANGUAGE,
            smart_format=True,
            encoding="linear16",
            channels=1,
            sample_rate=DG_SAMPLE_RATE,
            interim_results=True,
            utterance_end_ms=DG_UTTERANCE_END_MS,
            vad_events=True,
            endpointing=DG_ENDPOINTING,
        )
    
    def _setup_event_handlers(self):
        """Set up Deepgram event handlers"""
        
        def on_open(connection, open_event, **kwargs):
            logging.info("Deepgram Connection Open")
        
        def on_message(connection, result, **kwargs):
            if self.is_paused:
                return
            
            try:
                sentence = result.channel.alternatives[0].transcript
                if len(sentence) > 0:
                    self.on_speech_detected()
                
                if result.is_final:
                    self.is_finals.append(sentence)
                    if result.speech_final:
                        utterance = " ".join(self.is_finals).strip()
                        if utterance:
                            logging.info(f"Typing (Speech Final): {utterance}")
                            pyautogui.typewrite(utterance + ' ', interval=0.01)
                            self.session_transcript.append(utterance)
                            self.is_finals = []
                
            except Exception as e:
                logging.error(f"Error processing message: {e} - Data: {result}")
        
        def on_utterance_end(connection, utterance_end, **kwargs):
            if self.is_paused:
                return
                
            if self.is_finals:
                utterance = " ".join(self.is_finals).strip()
                if utterance:
                    logging.info(f"Typing (Utterance End): {utterance}")
                    pyautogui.typewrite(utterance + ' ', interval=0.01)
                    self.session_transcript.append(utterance)
                self.is_finals = []
                self.on_speech_detected()
            
            logging.debug("Utterance End received")
        
        def on_speech_started(connection, speech_started, **kwargs):
            if self.is_paused:
                return
                
            logging.debug("Speech Started")
            self.on_speech_detected()
        
        def on_metadata(connection, metadata, **kwargs):
            logging.debug(f"Metadata: {metadata}")
        
        def on_close(connection, close, **kwargs):
            logging.info(f"Deepgram Connection Closed: {close}")
        
        def on_error(connection, error, **kwargs):
            logging.error(f"Deepgram Error: {error}")
        
        def on_unhandled(connection, unhandled, **kwargs):
            logging.warning(f"Unhandled Websocket Message: {unhandled}")
        
        # Register event handlers
        self.connection.on(LiveTranscriptionEvents.Open, on_open)
        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
        self.connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
        self.connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
        self.connection.on(LiveTranscriptionEvents.Close, on_close)
        self.connection.on(LiveTranscriptionEvents.Error, on_error)
        self.connection.on(LiveTranscriptionEvents.Unhandled, on_unhandled)