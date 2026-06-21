# -*- coding: utf-8 -*-
import os
import site
import re
import sys
from datetime import datetime

# Automatically add NVIDIA DLL paths for ctranslate2
try:
    for p in site.getsitepackages():
        for sub in ("cudnn", "cublas", "cuda_runtime"):
            path = os.path.join(p, "nvidia", sub, "bin")
            if os.path.exists(path):
                os.add_dll_directory(path)
                os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]
except Exception:
    pass

import threading
import tempfile
import wave
import time
import logging
import traceback
import queue

# ── Logging ──────────────────────────────────────────
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictate.log")
logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

class StreamToLogger:
    def __init__(self, logger, level):
        self.logger, self.level = logger, level
    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())
    def flush(self): pass

sys.stdout = StreamToLogger(logging.getLogger("STDOUT"), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger("STDERR"), logging.ERROR)

def _excepthook(t, v, tb):
    logging.error("Uncaught exception:", exc_info=(t, v, tb))
sys.excepthook = _excepthook

logging.info("--- Application Started ---")

import queue
import tempfile
import wave
import re
import numpy as np
import pyaudiowpatch as pyaudio
import pygetwindow as gw
import win32api
import win32gui
import pystray
import sounddevice as sd
import keyboard
import pyautogui
import pyperclip
from PIL import Image, ImageDraw
from faster_whisper import WhisperModel
from PIL import Image, ImageDraw

# Discord Bot integration removed due to DAVE E2EE limitations

# tkinterdnd2 (drag-and-drop)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    import tkinter as tk
    HAS_DND = True
except ImportError:
    import tkinter as tk
    TkinterDnD = None
    HAS_DND = False

# Pyannote Diarization
try:
    from pyannote.audio import Pipeline
    import torch
    HAS_DIARIZATION = True
except ImportError:
    HAS_DIARIZATION = False

# Unidecode (Hinglish / romanization)
try:
    from unidecode import unidecode as _to_roman
    HAS_ROMAN = True
except ImportError:
    HAS_ROMAN = False
    def _to_roman(t): return t

# ── CONFIG ────────────────────────────────────────────
HOTKEY          = "`"
MODEL_SIZE      = "large-v3"
LANGUAGE        = "en"      # mic dictation language
SAMPLE_RATE     = 16000
SUPPORTED_AUDIO = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".opus", ".webm"}

# Dodo specific config
DODO_LOG_DIR       = r"C:\dodo-logs"
DODO_CHUNK_SECONDS = 15
DODO_OVERLAP_SEC   = 3
DODO_MIN_AUDIO_SEC = 2.0
DODO_VAD_SILENCE   = 500

LATIN_LANGS = {
    "en","es","fr","de","it","pt","nl","sv","da","no","fi","pl","cs","sk",
    "hr","ro","hu","tr","id","ms","tl","sw","cy","is","mt","sq","gl","ca",
}

pyautogui.FAILSAFE = False

logging.info("Loading Whisper model...")
model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="int8", local_files_only=True)
logging.info("Model loaded.")

diarization_pipeline = None
_dodo_force_flush = False

# ── Shared state ──────────────────────────────────────
recording     = False
audio_chunks  = []
record_thread = None
tray_icon     = None
ui_queue      = queue.Queue()   # background threads → UI
_file_queue   = queue.Queue()   # files waiting to be transcribed

_model_lock   = threading.Lock()

# Dodo state
_dodo_active      = False
_dodo_entry_count = 0
_dodo_loopback_buf= []
_dodo_mic_buf     = []
_dodo_buf_lock    = threading.Lock()
_dodo_source_name = "Unknown"

# ── Language display names ────────────────────────────
LANG_NAMES = {"en": "English", "hi": "Hindi"} # Truncated for brevity, model auto-detects

# ── Colour palette ────────────────────────────────────
C_BG      = "#0d0d14"
C_SURFACE = "#13131e"
C_CARD    = "#1a1a28"
C_BORDER  = "#252535"
C_ACCENT  = "#7c6bff"
C_GREEN   = "#00d4aa"
C_RED     = "#ff4f4f"
C_AMBER   = "#ffaa00"
C_TEXT    = "#e8e8f0"
C_MUTED   = "#5a5a70"
C_DIM     = "#2e2e42"

# ── Tray menu ─────────────────────────────────────────
def _make_icon(color, letter="W"):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([4, 4, 60, 60], fill=color)
    d.text((20, 15), letter, fill="white")
    return img

ICON_IDLE      = _make_icon((30,  150, 100))
ICON_RECORDING = _make_icon((220,  50,  50), "●")
ICON_THINKING  = _make_icon((200, 140,   0), "…")

def set_tray(icon_img, tooltip):
    if tray_icon:
        tray_icon.icon  = icon_img
        tray_icon.title = tooltip

def start_tray():
    global tray_icon
    menu = pystray.Menu(
        pystray.MenuItem("Open Panel", lambda i, it: ui_queue.put(("show_window",)), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda i, it: os._exit(0)),
    )
    tray_icon = pystray.Icon("whisper-dictate", ICON_IDLE, "Whisper — Ready", menu)
    tray_icon.run()

# ══════════════════════════════════════════════════════
# ── Dictation (Backtick) ──────────────────────────────
# ══════════════════════════════════════════════════════
def _record_audio():
    global audio_chunks
    audio_chunks = []
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            while recording:
                chunk, _ = stream.read(1024)
                audio_chunks.append(chunk.copy())
    except Exception as e:
        logging.error(f"Mic input error: {e}")

def _transcribe_and_type():
    set_tray(ICON_THINKING, "Whisper — Transcribing...")
    if not audio_chunks:
        set_tray(ICON_IDLE, "Whisper — Ready")
        return
    audio = np.concatenate(audio_chunks, axis=0).flatten()

    if len(audio) < SAMPLE_RATE * 0.5:
        set_tray(ICON_IDLE, "Whisper — Ready")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

    try:
        with _model_lock:
            segs, _ = model.transcribe(tmp, language=LANGUAGE, beam_size=1)
        text = " ".join(s.text.strip() for s in segs).strip()
        if text:
            pyperclip.copy(text + " ")
            time.sleep(0.15)
            pyautogui.hotkey("ctrl", "v")
    except Exception as e:
        logging.error(f"Mic transcription error: {e}")
    finally:
        try: os.remove(tmp)
        except Exception: pass
    set_tray(ICON_IDLE, "Whisper — Ready")

def on_press(e):
    global recording, record_thread
    if not recording:
        recording = True
        set_tray(ICON_RECORDING, "Whisper — Recording...")
        ui_queue.put(("mic_state", "recording"))
        record_thread = threading.Thread(target=_record_audio, daemon=True)
        record_thread.start()

def on_release(e):
    global recording, record_thread
    if recording:
        recording = False
        _rt = record_thread
        threading.Thread(target=_finish_and_transcribe, args=(_rt,), daemon=True).start()

def _finish_and_transcribe(rt):
    if rt: rt.join(timeout=3)
    ui_queue.put(("mic_state", "idle"))
    _transcribe_and_type()

keyboard.on_press_key(HOTKEY, on_press, suppress=True)
keyboard.on_release_key(HOTKEY, on_release, suppress=True)

# ══════════════════════════════════════════════════════
# ── Dodo Logger (Background) ──────────────────────────
# ══════════════════════════════════════════════════════

def toggle_dodo(state: bool):
    global _dodo_active, diarization_pipeline
    _dodo_active = state
    ui_queue.put(("dodo_state", "active" if state else "paused"))
    if state:
        logging.info("Dodo logger resumed.")
        if HAS_DIARIZATION and diarization_pipeline is None:
            logging.info("Lazy-loading Pyannote Diarization into VRAM...")
            try:
                from pyannote.audio import Pipeline
                import torch
                # Load .env file
                env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if "=" in line and not line.strip().startswith("#"):
                                k, v = line.strip().split("=", 1)
                                os.environ[k.strip()] = v.strip()
                
                hf_token = os.environ.get("HF_TOKEN")
                diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=hf_token
                )
                diarization_pipeline.to(torch.device("cuda"))
                logging.info("Pyannote loaded successfully.")
            except Exception as e:
                logging.error(f"Failed to lazy-load Pyannote: {e}")
    else:
        logging.info("Dodo logger paused.")
        if diarization_pipeline is not None:
            logging.info("Unloading Pyannote Diarization to free VRAM...")
            diarization_pipeline = None
            import gc
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

def force_flush_dodo():
    global _dodo_force_flush
    _dodo_force_flush = True
    logging.info("Forcing Dodo chunk flush.")

def _get_loopback_device(pa):
    try:
        def_out = pa.get_host_api_info_by_type(pyaudio.paWASAPI)["defaultOutputDevice"]
        def_name = pa.get_device_info_by_index(def_out)["name"]
        for dev in pa.get_loopback_device_info_generator():
            if def_name in dev["name"]: return dev
        for dev in pa.get_loopback_device_info_generator(): return dev
    except: pass
    return None

def _capture_loopback_worker(loop_dev):
    pa = pyaudio.PyAudio()
    l_ch = loop_dev["maxInputChannels"]
    l_fs = int(loop_dev["defaultSampleRate"])
    loop_stream = pa.open(format=pyaudio.paInt16, channels=l_ch, rate=l_fs,
                          input=True, input_device_index=loop_dev["index"], frames_per_buffer=int(l_fs*0.1))
    while True:
        if not _dodo_active:
            time.sleep(0.5)
            continue
        try:
            l_raw = loop_stream.read(int(l_fs * 0.1), exception_on_overflow=False)
            l_data = np.frombuffer(l_raw, dtype=np.int16).astype(np.float32) / 32768.0
            if len(l_data) > 0 and l_ch > 1: l_data = l_data.reshape(-1, l_ch).mean(axis=1)
            if len(l_data) > 0 and l_fs != SAMPLE_RATE:
                l_data = np.interp(np.linspace(0, len(l_data)-1, int(len(l_data)*SAMPLE_RATE/l_fs)), np.arange(len(l_data)), l_data).astype(np.float32)
            with _dodo_buf_lock:
                _dodo_loopback_buf.append(l_data)
        except: pass

def _capture_mic_worker(mic_dev):
    # We use sounddevice for the mic, which is identical to what the backtick dictation uses,
    # ensuring it reliably picks up the same default microphone.
    def mic_callback(indata, frames, t, status):
        if not _dodo_active: return
        with _dodo_buf_lock:
            _dodo_mic_buf.append(indata.copy().flatten())

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=mic_callback, blocksize=int(SAMPLE_RATE*0.1)):
            while True:
                time.sleep(1.0)
    except Exception as e:
        logging.error(f"Dodo mic worker error: {e}")

def _dodo_capture_thread():
    """Captures both system loopback AND default mic by spawning separate worker threads."""
    global _dodo_source_name
    pa = pyaudio.PyAudio()
    
    loop_dev = _get_loopback_device(pa)
    mic_dev = pa.get_default_input_device_info()
    
    if loop_dev:
        _dodo_source_name = f"{loop_dev['name']} + Mic"
        threading.Thread(target=_capture_loopback_worker, args=(loop_dev,), daemon=True).start()
    else:
        _dodo_source_name = "Microphone Only"
        
    threading.Thread(target=_capture_mic_worker, args=(mic_dev,), daemon=True).start()

def _dodo_process_loop():
    global _dodo_loopback_buf, _dodo_mic_buf
    while True:
        time.sleep(1.0)
        if not _dodo_active: continue

        with _dodo_buf_lock:
            audio_l = np.concatenate(_dodo_loopback_buf) if _dodo_loopback_buf else np.array([], dtype=np.float32)
            audio_m = np.concatenate(_dodo_mic_buf) if _dodo_mic_buf else np.array([], dtype=np.float32)
            
            length = max(len(audio_l), len(audio_m))
            
            global _dodo_force_flush
            
            # 1. Wait until we have at least 15 seconds of audio (unless forced)
            if length < SAMPLE_RATE * 15 and not _dodo_force_flush:
                continue

            # 2. Check if the last 2.0 seconds are silent
            check_len = int(SAMPLE_RATE * 2.0)
            rms_l = float(np.sqrt(np.mean(audio_l[-check_len:]**2))) if len(audio_l) > check_len else 0
            rms_m = float(np.sqrt(np.mean(audio_m[-check_len:]**2))) if len(audio_m) > check_len else 0
            
            is_speaking = (rms_l > 0.01 or rms_m > 0.01)

            # 3. If audio is continuous, keep waiting (unless we hit a 30s hard limit, or user forced flush)
            if is_speaking and length < SAMPLE_RATE * 30 and not _dodo_force_flush:
                continue

            # 4. We are ready to process!
            _dodo_force_flush = False
            _dodo_loopback_buf.clear()
            _dodo_mic_buf.clear()

            audio_l = np.clip(audio_l, -1.0, 1.0) if len(audio_l) > 0 else None
            audio_m = np.clip(audio_m, -1.0, 1.0) if len(audio_m) > 0 else None
            
            rms_l_full = float(np.sqrt(np.mean(audio_l**2))) if audio_l is not None else 0
            rms_m_full = float(np.sqrt(np.mean(audio_m**2))) if audio_m is not None else 0
            logging.info(f"DODO CHUNK: loop_len={len(audio_l) if audio_l is not None else 0} mic_len={len(audio_m) if audio_m is not None else 0} loop_rms={rms_l_full:.4f} mic_rms={rms_m_full:.4f}")

        threading.Thread(target=_dodo_transcribe, args=(audio_l, audio_m, datetime.now()), daemon=True).start()

def _dodo_transcribe(audio_l: np.ndarray, audio_m: np.ndarray, ts: datetime):
    global _dodo_entry_count
    
    all_segments = [] # (start_time, end_time, speaker, text)

    try:
        # Pass 1: Microphone (You)
        if audio_m is not None and len(audio_m) > SAMPLE_RATE * 0.5:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f: tmp_m = f.name
            with wave.open(tmp_m, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes((audio_m * 32767).astype(np.int16).tobytes())
            
            with _model_lock:
                m_segs_iter, _ = model.transcribe(tmp_m, language=LANGUAGE, beam_size=3, vad_filter=True, vad_parameters={"min_silence_duration_ms": DODO_VAD_SILENCE})
                for seg in m_segs_iter:
                    if seg.text.strip():
                        all_segments.append((seg.start, seg.end, "You", seg.text.strip()))
            try: os.remove(tmp_m)
            except: pass

        # Pass 2: Loopback (Others)
        if audio_l is not None and len(audio_l) > SAMPLE_RATE * 0.5:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f: tmp_l = f.name
            with wave.open(tmp_l, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes((audio_l * 32767).astype(np.int16).tobytes())

            with _model_lock:
                l_segs_iter, _ = model.transcribe(tmp_l, language=None, beam_size=3, vad_filter=True, vad_parameters={"min_silence_duration_ms": DODO_VAD_SILENCE})
                l_segs = list(l_segs_iter)

            diarization = None
            if diarization_pipeline:
                try:
                    import torch
                    waveform_tensor = torch.from_numpy(audio_l).unsqueeze(0)
                    diarization = diarization_pipeline({"waveform": waveform_tensor, "sample_rate": SAMPLE_RATE})
                except Exception as e:
                    logging.error(f"Diarization error: {e}")

            speaker_turns = []
            if diarization:
                if hasattr(diarization, "itertracks"): anno = diarization
                elif hasattr(diarization, "speaker_diarization"): anno = diarization.speaker_diarization
                else: anno = None
                if anno:
                    for turn, _, speaker in anno.itertracks(yield_label=True):
                        speaker_turns.append((turn.start, turn.end, speaker))

            for seg in l_segs:
                if not seg.text.strip(): continue
                
                # Assign speaker based on the center of the whisper segment
                w_mid = (seg.start + seg.end) / 2
                spk = "Unknown"
                for start, end, speaker in speaker_turns:
                    if start <= w_mid <= end:
                        spk = speaker
                        break
                        
                if spk == "Unknown" and speaker_turns:
                    closest_spk = "Unknown"
                    min_dist = 2.0
                    for start, end, speaker in speaker_turns:
                        dist = min(abs(w_mid - start), abs(w_mid - end))
                        if dist < min_dist:
                            min_dist = dist
                            closest_spk = speaker
                    spk = closest_spk
                
                all_segments.append((seg.start, seg.end, spk, seg.text.strip()))
                    
            try: os.remove(tmp_l)
            except: pass

        if not all_segments: return

        # Sort segments chronologically
        all_segments.sort(key=lambda x: x[0])
        
        formatted_lines = []
        for start, end, spk, text in all_segments:
            formatted_lines.append(f"**[{spk}]**: {text}")

        text = "\n".join(formatted_lines)

        if text:
            os.makedirs(DODO_LOG_DIR, exist_ok=True)
            path = os.path.join(DODO_LOG_DIR, ts.strftime("%Y-%m-%d") + ".md")
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# Dodo Log — {ts.strftime('%A, %d %B %Y')}\n\n*Audio source: {_dodo_source_name}*\n\n---\n\n")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"**[{ts.strftime('%H:%M:%S')}]**\n{text}\n\n")
            _dodo_entry_count += 1
            ui_queue.put(("dodo_entry", _dodo_entry_count))
            
    except Exception as e:
        logging.error(f"Dodo transcribe error: {e}")

# ══════════════════════════════════════════════════════
# ── File Transcription Worker ─────────────────────────
# ══════════════════════════════════════════════════════
def _parse_drop_paths(raw):
    raw = raw.strip()
    paths = re.findall(r"\{([^}]+)\}", raw)
    if not paths: paths = raw.split()
    return [p.strip() for p in paths if p.strip()]

def _file_worker():
    while True:
        filepath = _file_queue.get()
        try: _process_one_file(filepath)
        except Exception as e: ui_queue.put(("file_error", filepath, str(e)))
        finally: _file_queue.task_done()

def _process_one_file(filepath):
    ui_queue.put(("file_processing", filepath))
    try:
        from faster_whisper import WhisperModel
        import gc
        import torch
        logging.info("Loading heavy large-v3 model for batch processing...")
        batch_model = WhisperModel("large-v3", device="cuda", compute_type="int8", local_files_only=True)
        
        segs, info = batch_model.transcribe(filepath, language=None, beam_size=5, vad_filter=True, task="transcribe")
        original = " ".join(s.text.strip() for s in segs).strip()
        lang, prob = info.language, info.language_probability

        if lang and lang != "en":
            segs_en, _ = batch_model.transcribe(filepath, language=lang, beam_size=5, vad_filter=True, task="translate")
            english = " ".join(s.text.strip() for s in segs_en).strip()
        else:
            english = original

        hinglish = _to_roman(original) if (HAS_ROMAN and lang and lang not in LATIN_LANGS) else None
        ui_queue.put(("file_result", filepath, original, english, hinglish, lang, prob))
        
        # Unload the heavy model to free VRAM
        del batch_model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logging.info("Unloaded large-v3 model.")
        
    except Exception as e:
        ui_queue.put(("file_error", filepath, str(e)))

# ══════════════════════════════════════════════════════
# ── UI Components ─────────────────────────────────────
# ══════════════════════════════════════════════════════

class ResultCard(tk.Frame):
    def __init__(self, parent, filepath):
        super().__init__(parent, bg=C_CARD, padx=12, pady=10, highlightbackground=C_BORDER, highlightthickness=1)
        self.filepath = filepath
        self._views = {}
        self._current = "original"
        self._anim_step = 0
        self._done = False
        self._anim_id = None
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C_CARD)
        hdr.pack(fill="x", pady=(0, 6))
        fname = os.path.basename(self.filepath)
        tk.Label(hdr, text="🎵", font=("Segoe UI Emoji", 10), bg=C_CARD, fg=C_MUTED).pack(side="left", padx=(0, 6))
        tk.Label(hdr, text=fname[:35] + ("…" if len(fname)>38 else ""), font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_CARD).pack(side="left")
        
        self._lang_lbl = tk.Label(hdr, text="• Queued", font=("Segoe UI", 7, "bold"), fg=C_DIM, bg=C_CARD)
        self._lang_lbl.pack(side="right")
        self._stripe = tk.Frame(self, bg=C_BORDER, height=2)
        self._stripe.pack(fill="x", pady=(0, 8))
        self._toggle_row = tk.Frame(self, bg=C_CARD)
        
        self._txt_wrap = tk.Frame(self, bg=C_BORDER, padx=1, pady=1)
        self._txt_wrap.pack(fill="x")
        self._txt = tk.Text(self._txt_wrap, bg=C_SURFACE, fg=C_DIM, font=("Segoe UI", 9), relief="flat", wrap="word", padx=10, pady=8, state="disabled", height=5)
        self._txt.pack(fill="x")
        self._set_text("Queued…", C_DIM)
        
        br = tk.Frame(self, bg=C_CARD)
        br.pack(fill="x", pady=(8, 0))
        self._copy_btn = tk.Button(br, text="⎘  Copy", font=("Segoe UI", 8, "bold"), fg="white", bg=C_ACCENT, relief="flat", padx=10, pady=4, cursor="hand2", command=self._copy, state="disabled")
        self._copy_btn.pack(side="left")

    def start_processing(self):
        self._lang_lbl.config(text="• Processing…", fg=C_AMBER)
        self._stripe.config(bg=C_AMBER)
        self._animate()

    def _animate(self):
        if self._done: return
        self._anim_step += 1
        self._set_text(["Transcribing .", "Transcribing ..", "Transcribing ..."][self._anim_step % 3], C_MUTED)
        self._anim_id = self.after(500, self._animate)

    def set_result(self, orig, eng, hing, lang, prob):
        self._done = True
        if self._anim_id: self.after_cancel(self._anim_id)
        self._lang_lbl.config(text=f"{(lang or '?').upper()} {int((prob or 0)*100)}%", fg=C_GREEN)
        self._stripe.config(bg=C_GREEN)
        self._views = {"original": orig, "english": eng}
        if hing: self._views["hinglish"] = hing
        
        self._btn_orig = self._make_toggle("Original", "original")
        self._btn_en = self._make_toggle("English", "english")
        self._btn_hin = self._make_toggle("Hinglish", "hinglish") if hing else None
        
        self._toggle_row.pack(fill="x", pady=(0, 6), before=self._txt_wrap)
        self._copy_btn.config(state="normal")
        self._switch("original")

    def set_error(self, err):
        self._done = True
        if self._anim_id: self.after_cancel(self._anim_id)
        self._lang_lbl.config(text="Error", fg=C_RED)
        self._stripe.config(bg=C_RED)
        self._set_text(err, C_RED)

    def _make_toggle(self, label, key):
        btn = tk.Button(self._toggle_row, text=label, font=("Segoe UI", 8), fg=C_MUTED, bg=C_DIM, relief="flat", padx=12, pady=3, cursor="hand2", command=lambda k=key: self._switch(k))
        btn.pack(side="left", padx=(0, 4))
        return btn

    def _switch(self, key):
        self._current = key
        self._set_text(self._views.get(key, "(nothing)"), C_TEXT)
        for b, k in [(self._btn_orig, "original"), (self._btn_en, "english"), (getattr(self, "_btn_hin", None), "hinglish")]:
            if b: b.config(bg=C_ACCENT if k==key else C_DIM, fg="white" if k==key else C_MUTED)

    def _set_text(self, text, color):
        self._txt.config(state="normal", fg=color)
        self._txt.delete("1.0", "end")
        self._txt.insert("1.0", text)
        self._txt.config(state="disabled")

    def _copy(self):
        pyperclip.copy(self._views.get(self._current, ""))
        self._copy_btn.config(text="✓ Copied!")
        self.after(2000, lambda: self._copy_btn.config(text="⎘  Copy"))

class DictatePanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Omni Recorder")
        self.root.configure(bg=C_BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.withdraw()
        self._cards = {}
        self._build_ui()
        self._position_window()
        self._poll_queue()

    def _build_ui(self):
        tb = tk.Frame(self.root, bg="#0a0a10", height=44)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        tb.bind("<ButtonPress-1>", self._drag_start)
        tb.bind("<B1-Motion>", self._drag_motion)
        tk.Label(tb, text="◉", font=("Segoe UI", 13), fg=C_ACCENT, bg="#0a0a10").pack(side="left", padx=(14, 6), pady=10)
        tk.Label(tb, text="Omni Recorder", font=("Segoe UI", 11, "bold"), fg=C_TEXT, bg="#0a0a10").pack(side="left")
        self._status_badge = tk.Label(tb, text="● READY", font=("Segoe UI", 8, "bold"), fg=C_GREEN, bg="#0a0a10", padx=6)
        self._status_badge.pack(side="right", padx=4)
        xlbl = tk.Label(tb, text="✕", font=("Segoe UI", 10), fg=C_MUTED, bg="#0a0a10", cursor="hand2", padx=10)
        xlbl.pack(side="right")
        xlbl.bind("<Button-1>", lambda e: self.hide())
        tk.Frame(self.root, bg=C_BORDER, height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=C_BG, padx=14, pady=12)
        body.pack(fill="both", expand=True)

        # -- Backtick Hint
        mic = tk.Frame(body, bg=C_CARD, padx=12, pady=8, highlightbackground=C_BORDER, highlightthickness=1)
        mic.pack(fill="x", pady=(0, 12))
        tk.Label(mic, text="🎙️", font=("Segoe UI Emoji", 16), bg=C_CARD, fg=C_TEXT).pack(side="left", padx=(0, 10))
        col = tk.Frame(mic, bg=C_CARD)
        col.pack(side="left", fill="x", expand=True)
        tk.Label(col, text="Hold  `  (backtick) anywhere to dictate", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_CARD).pack(anchor="w")
        tk.Label(col, text="Types automatically at your cursor", font=("Segoe UI", 8), fg=C_MUTED, bg=C_CARD).pack(anchor="w")

        # -- Dodo Logger Section
        tk.Label(body, text="DODO LOGGER (MEETINGS & SYSTEM)", font=("Segoe UI", 7, "bold"), fg=C_MUTED, bg=C_BG).pack(anchor="w", pady=(0, 6))
        dodo = tk.Frame(body, bg=C_CARD, padx=12, pady=10, highlightbackground=C_BORDER, highlightthickness=1)
        dodo.pack(fill="x", pady=(0, 12))
        
        self.dodo_btn = tk.Button(dodo, text="▶ Start Logger", font=("Segoe UI", 9, "bold"), fg="white", bg=C_DIM, relief="flat", padx=12, pady=4, cursor="hand2", command=self._toggle_dodo)
        self.dodo_btn.pack(side="left")
        
        self.dodo_status = tk.Label(dodo, text="Paused", font=("Segoe UI", 9), fg=C_MUTED, bg=C_CARD)
        self.dodo_status.pack(side="left", padx=10)

        dodo_log_btn = tk.Button(dodo, text="📁 Logs", font=("Segoe UI", 8), fg=C_TEXT, bg=C_DIM, relief="flat", padx=8, pady=4, cursor="hand2", command=lambda: os.startfile(DODO_LOG_DIR) if os.path.exists(DODO_LOG_DIR) else None)
        dodo_log_btn.pack(side="right")
        
        dodo_flush_btn = tk.Button(dodo, text="⚡ Force Log", font=("Segoe UI", 8, "bold"), fg="white", bg=C_ACCENT, relief="flat", padx=8, pady=4, cursor="hand2", command=force_flush_dodo)
        dodo_flush_btn.pack(side="right", padx=10)

        # -- Drop Zone
        tk.Label(body, text="AUDIO FILE TRANSCRIPTION", font=("Segoe UI", 7, "bold"), fg=C_MUTED, bg=C_BG).pack(anchor="w", pady=(0, 6))
        dz_outer = tk.Frame(body, bg=C_BORDER, padx=1, pady=1)
        dz_outer.pack(fill="x")
        self._dz = tk.Frame(dz_outer, bg=C_SURFACE, height=70)
        self._dz.pack(fill="x")
        self._dz.pack_propagate(False)
        tk.Frame(self._dz, bg=C_SURFACE, height=4).pack(fill="x")
        self._dz_icon = tk.Label(self._dz, text="📂", font=("Segoe UI Emoji", 20), bg=C_SURFACE, fg=C_MUTED)
        self._dz_icon.pack()
        self._dz_lbl = tk.Label(self._dz, text="Drag & drop audio files here" if HAS_DND else "No drag drop support", font=("Segoe UI", 8), fg=C_MUTED, bg=C_SURFACE)
        self._dz_lbl.pack()

        if HAS_DND:
            for w in [self._dz, self._dz_icon, self._dz_lbl]:
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self._on_drop)

        # -- Results List
        rh = tk.Frame(body, bg=C_BG)
        rh.pack(fill="x", pady=(10, 6))
        tk.Label(rh, text="RESULTS", font=("Segoe UI", 7, "bold"), fg=C_MUTED, bg=C_BG).pack(side="left")
        tk.Button(rh, text="Clear All", font=("Segoe UI", 7), fg=C_MUTED, bg=C_BG, relief="flat", cursor="hand2", command=self._clear_all).pack(side="right")
        
        wrap = tk.Frame(body, bg=C_BG)
        wrap.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(wrap, bg=C_BG, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient="vertical", command=self._canvas.yview, width=8)
        self._results_inner = tk.Frame(self._canvas, bg=C_BG)
        self._canvas_win = self._canvas.create_window((0, 0), window=self._results_inner, anchor="nw")
        self._canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._results_inner.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._canvas_win, width=e.width))

    def _toggle_dodo(self):
        if not _dodo_active:
            toggle_dodo(True)
            self.dodo_btn.config(text="⏸ Pause Logger", bg=C_BORDER, fg=C_TEXT)
            self.dodo_status.config(text="Listening...", fg=C_GREEN)
        else:
            toggle_dodo(False)
            self.dodo_btn.config(text="▶ Start Logger", bg=C_DIM, fg="white")
            self.dodo_status.config(text="Paused", fg=C_MUTED)

    def _on_drop(self, event):
        paths = _parse_drop_paths(event.data)
        for p in [p for p in paths if os.path.splitext(p)[1].lower() in SUPPORTED_AUDIO]:
            card = ResultCard(self._results_inner, p)
            card.pack(fill="x", pady=(0, 8), padx=2)
            self._cards[p] = card
            _file_queue.put(p)

    def _clear_all(self):
        for c in self._cards.values(): c.destroy()
        self._cards.clear()

    def _poll_queue(self):
        try:
            while True:
                msg = ui_queue.get_nowait()
                if msg[0] == "show_window": self.show()
                elif msg[0] == "mic_state": self._status_badge.config(text="● REC" if msg[1]=="recording" else "● READY", fg=C_RED if msg[1]=="recording" else C_GREEN)
                elif msg[0] == "file_processing": self._cards[msg[1]].start_processing()
                elif msg[0] == "file_result": self._cards[msg[1]].set_result(*msg[2:])
                elif msg[0] == "file_error": self._cards[msg[1]].set_error(msg[2])
                elif msg[0] == "dodo_state":
                    active = (msg[1] == "active")
                    self.dodo_btn.config(text="⏸ Pause Logger" if active else "▶ Start Logger", bg=C_GREEN if active else C_DIM)
                    self.dodo_status.config(text=f"Recording... ({_dodo_entry_count} logs)" if active else "Paused", fg=C_TEXT if active else C_MUTED)
                elif msg[0] == "dodo_entry":
                    if _dodo_active: self.dodo_status.config(text=f"Recording... ({msg[1]} logs)")
        except queue.Empty: pass
        self.root.after(80, self._poll_queue)

    def _position_window(self):
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = 464, min(760, sh - 80)
        self.root.geometry(f"{w}x{h}+{sw-w-18}+{max(10, sh-h-56)}")

    def _drag_start(self, e): self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()
    def _drag_motion(self, e): self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")
    def show(self): self._position_window(); self.root.deiconify(); self.root.lift(); self.root.focus_force()
    def hide(self): self.root.withdraw()

# ══════════════════════════════════════════════════════
# ── Bootstrap ─────────────────────────────────────────
# ══════════════════════════════════════════════════════
threading.Thread(target=start_tray, daemon=True).start()
threading.Thread(target=_file_worker, daemon=True).start()
threading.Thread(target=_dodo_capture_thread, daemon=True).start()
threading.Thread(target=_dodo_process_loop, daemon=True).start()

if HAS_DND: root = TkinterDnD.Tk()
else: root = tk.Tk()
panel = DictatePanel(root)
root.mainloop()