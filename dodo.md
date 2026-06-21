# Dodo 🦤 — Always-On AI Companion (Dictate Module)
> *"Like a second brain that's always in the room with you"*

---

## The Vision

Dodo is not a separate application; it is an integrated **"Logger Module" within the Whisper Dictate dashboard**. It listens to everything happening on your computer — any call, any meeting, any voice conversation — and silently logs it in real time with timestamps, and language detection.

You can toggle it on, pause it, and view logs directly from the Dictate UI.

---

## Where It Lives & How It Works

Because Dodo is integrated into Dictate, it shares the same high-powered Whisper model (`large-v3`). 

| Context | How Dodo Captures It |
|---|---|
| **Google Meet, Zoom, Teams** | Captures system audio (what others say) + your mic (what you say) simultaneously. No plugins needed. |
| **Discord (Casual Voice Chat)** | Captures system audio + your mic, just like Google Meet. |
| **Discord (Server Bot Mode - Future)** | A dedicated Discord bot that joins the server, providing perfect speaker separation by Discord username. |
| **YouTube / Spotify / Podcasts** | Captures system audio only. |

---

## The Unified Architecture

By merging Dodo into Dictate, we get a single **Omni-recorder**:
1. **Backtick (`\``):** Instantly dictate at your cursor.
2. **Drag & Drop:** Transcribe and translate files.
3. **Dodo Toggle:** Record meetings and system audio in the background to daily `.md` files.

**Resource Efficiency:** All three features share *one* Whisper model in memory, saving ~3GB of VRAM. A smart locking system ensures that if you use the backtick while Dodo is logging, the backtick gets priority.

---

## The Log File Format

Log file: `C:\dodo-logs\YYYY-MM-DD.md` — one file per day.

```markdown
# Dodo Log — 2026-05-22

## 14:00 — Session Started
*Source: System Loopback + Microphone*

---

**[14:03:11]** Hum live drone 18,000 mein de rahe hain toh...
**[14:03:28]** Haan main agree karta hoon, value proposition...
**[14:03:45]** Theek hai next step kya hai...
```

---

## Build Phases (Unified App)

### Phase 1 — Integration (Current)
- [ ] Move WASAPI loopback capture into `dictate.py`.
- [ ] Add Dodo Start/Pause toggle to the Dictate UI.
- [ ] Add dual-capture (mix your Mic with System Audio so your side of the meeting is recorded too).
- [ ] Share the Whisper model safely via locks.

### Phase 2 — Smart Source Detection
- [ ] Detect which app is making audio (Chrome, Discord, Zoom) and tag the log entries automatically.

### Phase 3 — The Discord Bot
- [ ] A separate `discord.py` bot module managed from the dashboard that joins your voice channels for perfect per-user meeting notes.

### Phase 4 — Summarization
- [ ] Local LLM integration (Ollama) to summarize the daily log and extract action items.
