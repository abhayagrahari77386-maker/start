"""
🎭 AI Voice Clone Avatar — Backend Server
FastAPI server that chains OpenAI + ElevenLabs + Sync.so
to create a talking AI avatar with a cloned voice.
"""

import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from config import UPLOAD_DIR, OPENAI_API_KEY, ELEVENLABS_API_KEY, SYNC_API_KEY
from services import openai_service, elevenlabs_service, sync_service

app = FastAPI(
    title="Voice Clone AI",
    description="AI Avatar with cloned voice and lip sync",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded/generated files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Store face image paths per session
face_images: dict[str, str] = {}


# ── Health Check ──────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Check server health and API key status."""
    return {
        "status": "ok",
        "apis": {
            "openai": bool(OPENAI_API_KEY and OPENAI_API_KEY != "sk-your-openai-key-here"),
            "elevenlabs": bool(ELEVENLABS_API_KEY and ELEVENLABS_API_KEY != "your-elevenlabs-key-here"),
            "sync": bool(SYNC_API_KEY and SYNC_API_KEY != "your-sync-api-key-here"),
        },
    }


# ── Setup: Upload Voice + Face ────────────────────────────

@app.post("/api/setup")
async def setup_avatar(
    voice_sample: UploadFile = File(..., description="Voice audio sample (MP3/WAV, 30s+ recommended)"),
    face_image: UploadFile = File(..., description="Face photo (JPG/PNG, clear front-facing)"),
    session_id: str = Form(None),
):
    """
    Step 1: Upload a voice sample and face image.
    Creates a voice clone on ElevenLabs and stores the face for lip sync.
    """
    if not session_id:
        session_id = uuid.uuid4().hex

    try:
        # Save voice sample
        voice_ext = os.path.splitext(voice_sample.filename)[1] or ".mp3"
        voice_path = os.path.join(UPLOAD_DIR, f"voice_{session_id}{voice_ext}")
        with open(voice_path, "wb") as f:
            shutil.copyfileobj(voice_sample.file, f)

        # Save face image
        face_ext = os.path.splitext(face_image.filename)[1] or ".jpg"
        face_path = os.path.join(UPLOAD_DIR, f"face_{session_id}{face_ext}")
        with open(face_path, "wb") as f:
            shutil.copyfileobj(face_image.file, f)

        face_images[session_id] = face_path

        # Clone the voice on ElevenLabs
        voice_id = await elevenlabs_service.clone_voice(session_id, voice_path)

        return {
            "status": "success",
            "session_id": session_id,
            "voice_id": voice_id,
            "message": "Voice cloned and face uploaded successfully!",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


# ── Chat: Text Only Mode (cheaper) ───────────────────────

@app.post("/api/chat-text")
async def chat_text_only(
    message: str = Form(...),
    session_id: str = Form(...),
):
    """
    Text-only chat mode. Returns AI text response + TTS audio (no lip sync).
    Cheaper for testing — skips Sync.so API.
    """
    try:
        # 1. Get AI response from OpenAI
        ai_response = await openai_service.generate_response(session_id, message)
        emotion, clean_text = openai_service.parse_emotion(ai_response)

        # 2. Generate speech with cloned voice
        audio_path = None
        audio_url = None
        voice_id = elevenlabs_service.get_voice_id(session_id)

        if voice_id:
            audio_path = await elevenlabs_service.generate_speech(session_id, ai_response)
            audio_url = f"/uploads/{os.path.basename(audio_path)}"

        return {
            "status": "success",
            "response": ai_response,
            "emotion": emotion,
            "clean_text": clean_text,
            "audio_url": audio_url,
            "video_url": None,
            "mode": "text",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# ── Chat: Full Pipeline (Text + Voice + Lip Sync) ────────

@app.post("/api/chat")
async def chat_full_pipeline(
    message: str = Form(...),
    session_id: str = Form(...),
):
    """
    Full pipeline chat. Returns AI text + cloned voice audio + lip-synced video.
    Uses all 3 APIs: OpenAI → ElevenLabs → Sync.so
    """
    try:
        # 1. Get AI response from OpenAI
        ai_response = await openai_service.generate_response(session_id, message)
        emotion, clean_text = openai_service.parse_emotion(ai_response)

        # 2. Generate speech with cloned voice
        voice_id = elevenlabs_service.get_voice_id(session_id)
        if not voice_id:
            raise HTTPException(status_code=400, detail="No voice clone found. Please run /api/setup first.")

        audio_path = await elevenlabs_service.generate_speech(session_id, ai_response)
        audio_url = f"/uploads/{os.path.basename(audio_path)}"

        # 3. Get face image
        face_path = face_images.get(session_id)
        if not face_path:
            raise HTTPException(status_code=400, detail="No face image found. Please run /api/setup first.")

        # 4. Generate lip sync video
        job = await sync_service.generate_lipsync(face_path, audio_path)
        job_id = job.get("id")

        if not job_id:
            # Some APIs return the result directly
            video_url = job.get("outputUrl") or job.get("output_url")
            if video_url:
                local_video = await sync_service.download_video(video_url)
                return {
                    "status": "success",
                    "response": ai_response,
                    "emotion": emotion,
                    "clean_text": clean_text,
                    "audio_url": audio_url,
                    "video_url": f"/uploads/{os.path.basename(local_video)}",
                    "mode": "full",
                }

        # 5. Wait for lip sync to complete
        completed = await sync_service.wait_for_completion(job_id)
        video_url = completed.get("outputUrl") or completed.get("output_url") or completed.get("output", {}).get("url")

        if video_url:
            local_video = await sync_service.download_video(video_url)
            video_url = f"/uploads/{os.path.basename(local_video)}"
        else:
            video_url = None

        return {
            "status": "success",
            "response": ai_response,
            "emotion": emotion,
            "clean_text": clean_text,
            "audio_url": audio_url,
            "video_url": video_url,
            "mode": "full",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full pipeline failed: {str(e)}")


# ── Check Lip Sync Status ────────────────────────────────

@app.get("/api/status/{job_id}")
async def check_lipsync_status(job_id: str):
    """Check the status of a pending lip sync job."""
    try:
        status = await sync_service.check_status(job_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Clear Session ─────────────────────────────────────────

@app.post("/api/clear")
async def clear_session(session_id: str = Form(...)):
    """Clear conversation history and optionally delete cloned voice."""
    openai_service.clear_history(session_id)
    await elevenlabs_service.delete_voice(session_id)
    if session_id in face_images:
        del face_images[session_id]
    return {"status": "cleared", "session_id": session_id}


# ── Serve Frontend ────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/")
async def serve_index():
    """Serve the frontend."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{filename}")
async def serve_static(filename: str):
    """Serve static frontend files."""
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


if __name__ == "__main__":
    import uvicorn
    print("🎭 Voice Clone AI — Starting server...")
    print("   Open http://localhost:8001 in your browser")
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
