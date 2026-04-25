# Whisper Dictate 🎙️

### Free, Local, System-Wide Speech-to-Text for Windows

A lightweight dictation tool that types what you say — in any app, any text field, anywhere on Windows. No subscription, no internet required, 100% private.

---

## What It Does

- Hold the **backtick key** (`` ` ``) anywhere → speak → release → text is typed at your cursor
- Works in **every app** — browsers, Notepad, VS Code, WhatsApp Web, Word, Excel — everywhere
- Runs **100% locally** — your voice never leaves your PC
- Sits quietly in the **system tray** (green = ready, red = recording, orange = transcribing)
- **Zero cost** after setup — no API keys, no subscriptions

---

## Requirements

- Windows 10 or Windows 11
- Python 3.12 (auto-installed by `install.bat`)
- ~500MB free disk space (for Python packages + Whisper model)
- A working microphone

---

## First-Time Installation (New PC)

### Step 1 — Copy Files

Copy the entire `dictate-app` folder to `C:\dictate-app\` on the target PC.

Your folder should look like this:

```
C:\dictate-app\
├── dictate.py       ← main app
├── install.bat      ← run this once
├── run.bat          ← manual launcher
└── uninstall.bat    ← clean removal
```

### Step 2 — Run the Installer

Right-click `install.bat` → **Run as Administrator**

The installer will automatically:

1. Check if Python is installed (installs it if missing)
2. Install all required Python packages
3. Copy app files to `C:\dictate-app\`
4. Add the app to Windows startup (runs silently on every boot)
5. Launch the app immediately

> ⚠️ If Python was just installed, the installer will ask you to close and reopen it. Do that, then run `install.bat` again.

### Step 3 — First Launch Model Download

On the very first run, the app downloads the Whisper **base** model (~74MB). This is a one-time download. After that, the app works fully offline forever.

---

## How to Use

| Action                | What to do                                                |
| --------------------- | --------------------------------------------------------- |
| **Start dictating**   | Click inside any text field, then hold `` ` `` (backtick) |
| **Stop & transcribe** | Release the backtick key                                  |
| **Check status**      | Look at the tray icon (bottom-right near clock)           |
| **Quit the app**      | Right-click tray icon → Quit                              |
| **Relaunch manually** | Double-click `run.bat`                                    |

### Tray Icon Colors

| Color     | Meaning                                  |
| --------- | ---------------------------------------- |
| 🟢 Green  | Ready — waiting for you to hold backtick |
| 🔴 Red    | Recording your voice                     |
| 🟠 Orange | Transcribing (processing speech)         |

---

## Configuration

Open `C:\dictate-app\dictate.py` in Notepad to change settings:

```python
# ── CONFIG ─────────────────────────────────────────
HOTKEY      = "`"       # Change to any key e.g. "right alt", "f9"
MODEL_SIZE  = "base"    # tiny / base / small / medium
LANGUAGE    = "en"      # en, hi, auto
SAMPLE_RATE = 16000
# ───────────────────────────────────────────────────
```

### Model Size Guide

| Model    | Size   | Speed   | Accuracy | Best For                    |
| -------- | ------ | ------- | -------- | --------------------------- |
| `tiny`   | 39 MB  | Fastest | Basic    | Quick testing               |
| `base`   | 74 MB  | Fast    | Good     | **Daily use (recommended)** |
| `small`  | 244 MB | Medium  | Better   | Hindi / mixed language      |
| `medium` | 769 MB | Slow    | High     | Maximum accuracy            |

### Language Codes

| Language    | Code   |
| ----------- | ------ |
| English     | `en`   |
| Hindi       | `hi`   |
| Auto-detect | `auto` |
| Spanish     | `es`   |
| French      | `fr`   |

---

## Sharing / Installing on Another PC

1. Copy the `C:\dictate-app\` folder to a USB drive or share via Google Drive / WhatsApp
2. On the new PC, paste it to `C:\dictate-app\`
3. Right-click `install.bat` → **Run as Administrator**
4. Done ✅

---

## Uninstall

Right-click `uninstall.bat` → **Run as Administrator**

This will:

- Stop the running app
- Remove it from Windows startup
- Delete all app files

---

## Troubleshooting

### App is not typing in some fields

Some apps (like administrator-level windows or UAC prompts) block automated input. This is a Windows security restriction. Try running `run.bat` as Administrator.

```
Right-click run.bat → Run as Administrator
```

### Hotkey not working

Another app may be capturing the backtick key. Change the hotkey in `dictate.py`:

```python
HOTKEY = "f9"        # Use F9 instead
# or
HOTKEY = "right alt" # Use Right Alt
```

### Text types garbled characters (special chars issue)

`pyautogui.typewrite()` has issues with special characters. For symbols, punctuation or non-ASCII text, change the typing method in `dictate.py`. Replace:

```python
pyautogui.typewrite(text + " ", interval=0.03)
```

With:

```python
import pyperclip
pyperclip.copy(text + " ")
time.sleep(0.1)
pyautogui.hotkey("ctrl", "v")
```

### App crashes on startup

Run manually to see the error:

```
python C:\dictate-app\dictate.py
```

Paste the error output for support.

### Microphone not detected

Check that your mic is set as the **default recording device** in Windows Sound Settings:

```
Right-click speaker icon → Sound Settings → Input → Choose your microphone
```

---

## Package Dependencies

| Package          | Purpose                             |
| ---------------- | ----------------------------------- |
| `faster-whisper` | Local speech-to-text engine         |
| `sounddevice`    | Microphone audio capture            |
| `numpy`          | Audio data processing               |
| `keyboard`       | Global hotkey listener              |
| `pyautogui`      | Simulated typing into active window |
| `pystray`        | System tray icon                    |
| `pillow`         | Tray icon image generation          |

---

## Privacy

- ✅ All audio processing happens **on your device**
- ✅ No audio is ever sent to any server
- ✅ No account, login, or internet connection required
- ✅ No telemetry or usage tracking

---

## Built With

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — optimized local Whisper inference
- OpenAI Whisper model weights (MIT License)
- Python 3.12

---

_Built for internal use by Klyx. Free to use and modify._
