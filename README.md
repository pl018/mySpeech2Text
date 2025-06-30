# Speech-to-Text App (Always-On Listening)

A real-time speech transcription application using Deepgram API that automatically types transcribed text into any application.

## 🚀 Quick Start

### Prerequisites
1. Python 3.7+
2. Deepgram API key (from [deepgram.com](https://deepgram.com))

### Setup
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment setup:**
   - The `.env` file is already configured with your API key
   - For new setups, copy `.env.example` to `.env` and add your key

3. **Run the application:**
   ```bash
   python main.py
   ```

## 🎯 Usage Instructions

### Controls & Hotkeys
| Action | Method | Description |
|--------|---------|-------------|
| **Start/Stop** | `Ctrl+Alt+\` (Global) | Toggle transcription from anywhere |
| **Pause/Resume** | Click ⏸️ button | Pause without stopping |
| **View Transcript** | Click 📄 button | Open saved transcript file |
| **Reset Interface** | Click 🔄 button | Reset after stopping |
| **Close App** | `Esc` key | Close when window focused |
| **Drag Window** | Click & drag | Move the floating window |

### Visual States
- **🎤 Red**: Recording active
- **⏸️ Orange**: Paused  
- **Idle Gray**: Not recording
- **Auto-stop**: After 20 seconds of silence

### File Outputs
- **Logs**: `logs/session_YYYYMMDD_HHMMSS.log`
- **Transcripts**: `transcripts/transcript_YYYYMMDD_HHMMSS.txt`

## 🧪 Testing Checklist

### Basic Functionality
- [ ] Launch app: `python main.py`
- [ ] Global hotkey works: `Ctrl+Alt+\`
- [ ] Speech gets transcribed and typed into text editor
- [ ] Auto-stop on silence (20 seconds)

### GUI Controls
- [ ] Pause/resume button works
- [ ] Transcript viewing opens file
- [ ] Window dragging works
- [ ] Close with Esc key

### File Generation
- [ ] Log files created in `logs/`
- [ ] Transcript files in `transcripts/`

## 🏗️ Build Executable

```bash
python build_exe.py
```

Creates `dist/SpeechToText.exe` with all dependencies included.

## 🔧 Configuration

Edit `config.py` to customize:
- Hotkey combination
- Silence timeout duration
- UI appearance settings
- Deepgram model parameters

## 📁 Project Structure

```
├── main.py                    # Entry point
├── config.py                  # Configuration settings
├── transcription/
│   ├── agent.py              # Main transcription logic
│   └── deepgram_client.py    # Deepgram API client
├── ui/
│   └── gui.py                # GUI implementation
├── utils/
│   └── logger.py             # Logging utilities
├── logs/                     # Session logs
└── transcripts/              # Saved transcripts
``` 