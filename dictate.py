import os
import site

# Automatically add NVIDIA DLL paths for ctranslate2
try:
    for p in site.getsitepackages():
        cudnn_path = os.path.join(p, "nvidia", "cudnn", "bin")
        cublas_path = os.path.join(p, "nvidia", "cublas", "bin")
        cudart_path = os.path.join(p, "nvidia", "cuda_runtime", "bin")
        if os.path.exists(cudnn_path):
            os.add_dll_directory(cudnn_path)
            os.environ["PATH"] = cudnn_path + os.pathsep + os.environ["PATH"]
        if os.path.exists(cublas_path):
            os.add_dll_directory(cublas_path)
            os.environ["PATH"] = cublas_path + os.pathsep + os.environ["PATH"]
        if os.path.exists(cudart_path):
            os.add_dll_directory(cudart_path)
            os.environ["PATH"] = cudart_path + os.pathsep + os.environ["PATH"]
except Exception:
    pass

import threading
import tempfile
import wave
import time
import sys
import logging
import traceback

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dictate.log')
logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class StreamToLogger(object):
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())
    def flush(self):
        pass

sys.stdout = StreamToLogger(logging.getLogger('STDOUT'), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger('STDERR'), logging.ERROR)

def my_excepthook(type, value, tb):
    logging.error("Uncaught exception:", exc_info=(type, value, tb))

sys.excepthook = my_excepthook

logging.info("--- Application Started ---")
import numpy as np
import sounddevice as sd
import keyboard
import pyautogui
import pyperclip
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw, ImageFont
import pystray

# ── CONFIG ─────────────────────────────────────────
HOTKEY      = "`"
MODEL_SIZE  = "large-v3"
LANGUAGE    = "en"
SAMPLE_RATE = 16000
# ───────────────────────────────────────────────────

pyautogui.FAILSAFE = False

print("⏳ Loading Whisper model...")
model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16", local_files_only=True)
print(f"✅ Ready! Hold [{HOTKEY}] to dictate.\n")

recording     = False
audio_chunks  = []
lock          = threading.Lock()
record_thread = None
tray_icon     = None

# ── Tray icon images ────────────────────────────────
def make_icon(color, letter="W"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=color)
    d.text((22, 16), letter, fill="white")
    return img

ICON_IDLE     = make_icon((30, 150, 100))   # green  — ready
ICON_RECORDING= make_icon((220, 50, 50),  "●")  # red    — recording
ICON_THINKING = make_icon((200, 140, 0),  "…")  # orange — transcribing

def set_tray(icon_img, tooltip):
    if tray_icon:
        tray_icon.icon  = icon_img
        tray_icon.title = tooltip

# ── Audio ───────────────────────────────────────────
def record_audio():
    global audio_chunks
    audio_chunks = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        while recording:
            chunk, _ = stream.read(1024)
            with lock:
                audio_chunks.append(chunk.copy())

def transcribe_and_type():
    set_tray(ICON_THINKING, "Whisper — Transcribing...")
    with lock:
        if not audio_chunks:
            set_tray(ICON_IDLE, "Whisper — Ready (hold ` to dictate)")
            return
        audio = np.concatenate(audio_chunks, axis=0).flatten()

    if len(audio) < SAMPLE_RATE * 0.5:
        print("⚠️  Too short, ignored.")
        set_tray(ICON_IDLE, "Whisper — Ready (hold ` to dictate)")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

    print("🎙️  Transcribing...", end=" ", flush=True)
    try:
        segments, _ = model.transcribe(tmp_path, language=LANGUAGE, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments).strip()

        if text:
            print(f"→ {text}")
            pyperclip.copy(text + " ")
            time.sleep(0.15)
            pyautogui.hotkey('ctrl', 'v')
        else:
            print("(nothing detected)")
    except Exception as e:
        print(f"ERROR during transcription: {e}")
        traceback.print_exc()

    set_tray(ICON_IDLE, "Whisper — Ready (hold ` to dictate)")

# ── Hotkey ──────────────────────────────────────────
def on_press(e):
    global recording, record_thread
    if not recording:
        recording = True
        set_tray(ICON_RECORDING, "Whisper — Recording...")
        print("🔴 Recording...", end=" ", flush=True)
        record_thread = threading.Thread(target=record_audio, daemon=True)
        record_thread.start()

def on_release(e):
    global recording, record_thread
    if recording:
        recording = False
        if record_thread:
            record_thread.join(timeout=3)
        threading.Thread(target=transcribe_and_type, daemon=True).start()

keyboard.on_press_key(HOTKEY,   on_press,   suppress=True)
keyboard.on_release_key(HOTKEY, on_release, suppress=True)

# ── Tray ────────────────────────────────────────────
def quit_app(icon, item):
    icon.stop()
    sys.exit(0)

def start_tray():
    global tray_icon
    menu = pystray.Menu(
        pystray.MenuItem("Whisper Dictate — Ready", None, enabled=False),
        pystray.MenuItem("Hold  `  to dictate",     None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )
    tray_icon = pystray.Icon("whisper-dictate", ICON_IDLE,
                              "Whisper — Ready (hold ` to dictate)", menu)
    tray_icon.run()

# ── Start ────────────────────────────────────────────
tray_thread = threading.Thread(target=start_tray, daemon=True)
tray_thread.start()

print("🟢 Running in system tray. Hold backtick anywhere to dictate.\n")
keyboard.wait()