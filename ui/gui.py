import customtkinter as ctk
import logging
import os
import sys
import tkinter as tk
from PIL import Image, ImageTk  # For loading the icon
from config import (
    UI_OPACITY, BTN_RECORD_ICON, BTN_STOP_ICON, BTN_PAUSE_ICON, BTN_PLAY_ICON, 
    BTN_TRANSCRIPT_ICON, BTN_RECORD_SIZE, BTN_CONTROL_SIZE, BTN_RECORD_COLOR,
    BTN_RECORD_ACTIVE_COLOR, BTN_CONTROL_COLOR, BTN_DISABLED_COLOR, BTN_PAUSED_COLOR
)

class TranscriptionGUI:
    def __init__(self, width, height, opacity=UI_OPACITY):
        self._drag_data = {"x": 0, "y": 0}  # For window dragging
        
        # Create root window
        self.root = ctk.CTk()
        self.root.title("Transcription Agent")  # Title won't be visible
        self.root.geometry(f"{width}x{height}")
        self.root.resizable(False, False)
        self.root.wm_attributes("-topmost", True)  # Always on top
        
        # Set application icon
        self._set_app_icon()
        
        # Make window borderless
        self.root.overrideredirect(1)
        
        # Try setting transparency
        try:
            self.root.attributes("-alpha", opacity) # Use the opacity from config
        except ctk.TclError:
            logging.warning("Window transparency not supported on this system.")
            
        # Apply CustomTkinter settings
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create frames and controls
        self._create_ui_components()
        
        # Set up drag bindings
        self._setup_drag_bindings()
    
    def _set_app_icon(self):
        """Set the application icon in the taskbar"""
        try:
            # Find the icon file
            # First check for the ICO file (preferred)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, "mic.ico")
            
            # If running as bundled app, check the PyInstaller _MEIPASS path
            if not os.path.exists(icon_path) and hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "mic.ico")
            
            # Fallback to PNG if ICO not found
            if not os.path.exists(icon_path):
                png_path = os.path.join(base_dir, "mic.png")
                if os.path.exists(png_path):
                    icon_path = png_path
                elif hasattr(sys, '_MEIPASS'):
                    icon_path = os.path.join(sys._MEIPASS, "mic.png")
            
            # If icon exists, set it
            if os.path.exists(icon_path):
                # Different handling for ICO vs PNG
                if icon_path.lower().endswith('.ico'):
                    # On Windows, we can use iconbitmap for ICO files
                    if sys.platform == "win32":
                        self.root.iconbitmap(icon_path)
                    else:
                        # On non-Windows, we still need to use PhotoImage
                        icon_image = Image.open(icon_path)
                        icon_photo = ImageTk.PhotoImage(icon_image)
                        self.root.iconphoto(True, icon_photo)
                else:
                    # For PNG files, use PhotoImage
                    icon_image = Image.open(icon_path)
                    icon_photo = ImageTk.PhotoImage(icon_image)
                    self.root.iconphoto(True, icon_photo)
                
                logging.info(f"Set application icon from: {icon_path}")
            else:
                logging.warning(f"Icon file not found: {icon_path}")
        except Exception as e:
            logging.error(f"Error setting application icon: {e}")
    
    def _create_ui_components(self):
        # Main frame covering the whole window (for background/dragging)
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill=ctk.BOTH, expand=True)
        
        # Top "Title Bar" Area
        self.top_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_frame.pack(fill=ctk.X, padx=5, pady=(2, 0))
        
        # Status Label (Top Left)
        self.status_label = ctk.CTkLabel(self.top_frame, text="Idle", text_color="gray", anchor="w")
        self.status_label.pack(side=ctk.LEFT, padx=(3, 0))
        
        # Transcript Button (Top Right)
        icon_font_small = ctk.CTkFont(size=20)  # Size for icon buttons
        self.transcript_button = ctk.CTkButton(
            self.top_frame, 
            text=BTN_TRANSCRIPT_ICON, 
            width=25, 
            height=25, 
            font=icon_font_small,
            text_color=BTN_CONTROL_COLOR,  
            fg_color="transparent",
            hover=False, 
            command=None,  # Will be set by the agent
            state=ctk.DISABLED # Initially disabled
        )
        self.transcript_button.pack(side=ctk.RIGHT, padx=(0, 5))
        
        # Bottom Control Buttons Area
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill=ctk.X, pady=(0, 5))
        
        # Three equal columns: Pause | Record | Reset
        for i in range(3):
            self.button_frame.columnconfigure(i, weight=1)
        
        icon_font_large = ctk.CTkFont(size=32)  # Larger icons for main controls
        icon_font_small = ctk.CTkFont(size=20)  # Slightly smaller for controls
        
        # Pause / Resume Button (left)
        self.pause_resume_button = ctk.CTkButton(
            self.button_frame, 
            text=BTN_PAUSE_ICON, 
            width=BTN_CONTROL_SIZE, 
            height=BTN_CONTROL_SIZE, 
            font=icon_font_small, 
            text_color=BTN_CONTROL_COLOR, 
            fg_color="transparent", 
            border_width=0,
            border_color=None,
            hover=False, 
            command=None,  # Will be set by the agent
            state=ctk.DISABLED
        )
        self.pause_resume_button.grid(row=0, column=0, padx=5)
        
        # Record Button (center)
        self.record_button = ctk.CTkButton(
            self.button_frame, 
            text=BTN_RECORD_ICON, 
            width=BTN_RECORD_SIZE, 
            height=BTN_RECORD_SIZE, 
            font=icon_font_large, 
            text_color=BTN_RECORD_COLOR, 
            fg_color="transparent", 
            border_width=0,
            border_color=None,
            hover=False, 
            command=None,  # Will be set by the agent
            state=ctk.NORMAL # Start enabled
        )
        self.record_button.grid(row=0, column=1, padx=5)
        
        # Stop Button (right)
        self.stop_button = ctk.CTkButton(
            self.button_frame, 
            text=BTN_STOP_ICON, 
            width=BTN_CONTROL_SIZE, 
            height=BTN_CONTROL_SIZE, 
            font=icon_font_small, 
            text_color=BTN_CONTROL_COLOR, 
            fg_color="transparent", 
            border_width=0,
            border_color=None,
            hover=False, 
            command=None  # Will be set by the agent
        )
        self.stop_button.grid(row=0, column=2, padx=5)
    
    def _setup_drag_bindings(self):
        # Bind dragging events to main components
        for widget in [self.root, self.main_frame, self.top_frame, self.status_label, 
                      self.button_frame]:
            widget.bind("<ButtonPress-1>", self.on_drag_start)
            widget.bind("<ButtonRelease-1>", self.on_drag_stop)
            widget.bind("<B1-Motion>", self.on_drag_motion)
    
    def on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def on_drag_stop(self, event):
        self._drag_data["x"] = 0
        self._drag_data["y"] = 0
    
    def on_drag_motion(self, event):
        # Calculate x and y coordinates of mouse cursor
        x = self.root.winfo_pointerx() - self._drag_data["x"]
        y = self.root.winfo_pointery() - self._drag_data["y"]
        self.root.geometry(f"+{x}+{y}")
    
    def update_state(self, is_running, is_paused, has_transcript_file):
        """Update the UI state based on application state"""
        # Determine icon/text/color based on state
        if is_running:
            record_icon = BTN_RECORD_ICON  # Keep record icon consistent but dim it
            record_color = BTN_RECORD_ACTIVE_COLOR  # Darker red when recording
            pause_icon = BTN_PLAY_ICON if is_paused else BTN_PAUSE_ICON  # Play icon if paused, pause otherwise
            pause_color = BTN_PAUSED_COLOR if is_paused else BTN_CONTROL_COLOR
            pause_state = ctk.NORMAL
            stop_state = ctk.NORMAL
            transcript_state = ctk.DISABLED # Disable transcript button while running
            if is_paused:
                status_text = "Paused"
                status_color = "orange"
            else: 
                status_text = "Running"
                status_color = "green"
        else:
            record_icon = BTN_RECORD_ICON  # Circle icon for record when idle
            record_color = BTN_RECORD_COLOR
            pause_icon = BTN_PAUSE_ICON  # Default icon when disabled
            pause_color = BTN_DISABLED_COLOR  # Color when disabled
            pause_state = ctk.DISABLED
            stop_state = ctk.DISABLED  # Disable stop button when idle
            transcript_state = ctk.NORMAL if has_transcript_file else ctk.DISABLED
            status_text = "Idle"
            status_color = "gray"
        
        # Update GUI elements
        self.status_label.configure(text=status_text, text_color=status_color)
        self.record_button.configure(text=record_icon, text_color=record_color, state=ctk.NORMAL)
        self.pause_resume_button.configure(text=pause_icon, text_color=pause_color, state=pause_state)
        self.stop_button.configure(state=stop_state)
        self.transcript_button.configure(state=transcript_state)
    
    def set_command_callbacks(self, toggle_func, pause_func, transcript_func, stop_func):
        """Set the callback functions for the buttons"""
        self.record_button.configure(command=toggle_func)
        self.pause_resume_button.configure(command=pause_func)
        self.transcript_button.configure(command=transcript_func)
        self.stop_button.configure(command=stop_func)
    
    def add_escape_handler(self, handler):
        """Add escape key handler to close application"""
        self.root.bind("<Escape>", lambda e: handler())
    
    def start(self):
        """Start the GUI main loop"""
        self.root.mainloop()
        
    def schedule_task(self, delay, callback):
        """Schedule a task to run after delay milliseconds"""
        self.root.after(delay, callback)