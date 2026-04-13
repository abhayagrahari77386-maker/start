# 🎭 Voice Clone AI

AI-powered avatar that speaks with your cloned voice and animated lip sync.

## How It Works

1. **Upload** a voice sample (30s+ audio) and a face image
2. **Chat** with the AI — it responds with your cloned voice
3. **Watch** the avatar speak with lip-synced video

### Pipeline
```
User Message → OpenAI GPT-4o → ElevenLabs TTS (cloned voice) → Sync.so Lip Sync → Video Output
```

## Setup

### 1. Get API Keys

| Service | URL | What For |
|---------|-----|----------|
| OpenAI | https://platform.openai.com/api-keys | AI brain (GPT-4o) |
| ElevenLabs | https://elevenlabs.io | Voice cloning + TTS |
| Sync.so | https://sync.so/settings/api-keys | Lip sync video |

### 2. Configure

```bash
cd backend
copy .env.example .env
# Edit .env and add your API keys
```

### 3. Install & Run

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Start the server
python main.py
```

Then open **http://localhost:8000** in your browser.

## Usage

1. Upload a **voice sample** (MP3/WAV, 30 seconds or more)
2. Upload a **face image** (clear, front-facing photo)
3. Click **"Clone Voice & Setup Avatar"**
4. Start chatting!

### Modes
- **💬 Text + Audio** — Faster, cheaper. Returns text + cloned voice audio
- **🎬 Full Video** — Returns lip-synced talking head video (uses Sync.so credits)

## Tech Stack

- **Backend:** Python + FastAPI
- **Brain:** OpenAI GPT-4o
- **Voice:** ElevenLabs (instant voice cloning)
- **Lip Sync:** Sync.so API
- **Frontend:** Vanilla HTML/CSS/JS
