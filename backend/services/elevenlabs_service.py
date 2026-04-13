"""
ElevenLabs Service — Voice cloning and text-to-speech.
Clones a voice from an audio sample and generates speech in that voice.
"""

import os
import uuid
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from config import ELEVENLABS_API_KEY, ELEVENLABS_MODEL, UPLOAD_DIR


client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Store cloned voice IDs per session
cloned_voices: dict[str, str] = {}


def _get_free_tier_voice_id() -> str:
    """
    Fetch the first voice from the user's own ElevenLabs account.
    This works on free tier because it's YOUR voice — not a library voice.
    Falls back to a known premade voice ID only if the account has no voices.
    """
    try:
        response = client.voices.get_all()
        voices = response.voices if hasattr(response, "voices") else list(response)
        # Filter to only "premade" category voices — always accessible on free tier
        premade = [v for v in voices if getattr(v, "category", "") == "premade"]
        if premade:
            print(f"Free-tier fallback: using premade voice '{premade[0].name}' ({premade[0].voice_id})")
            return premade[0].voice_id
        # If no premade, try any voice
        if voices:
            print(f"Free-tier fallback: using first available voice '{voices[0].name}' ({voices[0].voice_id})")
            return voices[0].voice_id
    except Exception as fetch_err:
        print(f"Warning: Could not fetch voices list: {fetch_err}")
    # Last resort hardcoded premade voice (Adam — universally available on free tier)
    return "pNInz6obpgDQGcFmaJgB"


async def clone_voice(session_id: str, audio_file_path: str, voice_name: str = None) -> str:
    """
    Clone a voice from an audio sample file.
    Returns the voice ID of the cloned voice.
    """
    if voice_name is None:
        voice_name = f"clone_{session_id[:8]}"

    try:
        with open(audio_file_path, "rb") as f:
            voice = client.voices.ivc.create(
                name=voice_name,
                files=[f],
                description=f"Cloned voice for session {session_id}",
            )
        voice_id = voice.voice_id
        print(f"Voice cloned successfully! Voice ID: {voice_id}")
    except Exception as e:
        error_msg = str(e).lower()
        if "payment" in error_msg or "subscription" in error_msg or "paid_plan" in error_msg:
            print("Free tier detected. Fetching your account's own voices as fallback...")
            voice_id = _get_free_tier_voice_id()
            print(f"Using fallback voice ID: {voice_id}")
        else:
            raise e

    cloned_voices[session_id] = voice_id
    return voice_id


async def generate_speech(session_id: str, text: str) -> str:
    """
    Generate speech audio from text using the cloned voice.
    Returns the path to the generated audio file.
    """
    voice_id = cloned_voices.get(session_id)
    if not voice_id:
        raise ValueError("No cloned voice found for this session. Please upload a voice sample first.")

    # Clean emotion tags from text before speaking
    import re
    clean_text = re.sub(r'\[\w+\]\s*', '', text)

    audio_generator = client.text_to_speech.convert(
        voice_id=voice_id,
        text=clean_text,
        model_id=ELEVENLABS_MODEL,
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.8,
            style=0.6,
            use_speaker_boost=True,
        ),
    )

    # Save audio to file
    output_path = os.path.join(UPLOAD_DIR, f"speech_{uuid.uuid4().hex[:12]}.mp3")
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    print(f"Speech generated: {output_path}")
    return output_path


def get_voice_id(session_id: str) -> str | None:
    """Get the cloned voice ID for a session."""
    return cloned_voices.get(session_id)


async def delete_voice(session_id: str):
    """Delete the cloned voice from ElevenLabs."""
    voice_id = cloned_voices.get(session_id)
    if voice_id:
        try:
            client.voices.delete(voice_id)
            del cloned_voices[session_id]
            print(f"Voice {voice_id} deleted")
        except Exception as e:
            print(f"Failed to delete voice: {e}")
