"""
Google Gemini — conversational brain for the avatar.
Same behavior as the former OpenAI layer: emotion-tagged replies + session history.
"""

import re

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT

# In-memory: alternating user / model turns (Gemini chat format)
conversations: dict[str, list] = {}

_model = None
_model_sig: tuple[str, str] | None = None


def _get_model():
    global _model, _model_sig
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key-here":
        raise RuntimeError(
            "Set GEMINI_API_KEY in backend/.env (get a key at https://aistudio.google.com/apikey)."
        )
    sig = (GEMINI_API_KEY, GEMINI_MODEL)
    if _model is None or _model_sig != sig:
        genai.configure(api_key=GEMINI_API_KEY)
        _model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )
        _model_sig = sig
    return _model


def get_or_create_history(session_id: str) -> list:
    if session_id not in conversations:
        conversations[session_id] = []
    return conversations[session_id]


async def generate_response(session_id: str, user_message: str) -> str:
    history = get_or_create_history(session_id)

    if len(history) > 20:
        history[:] = history[-20:]
        conversations[session_id] = history

    history.append({"role": "user", "parts": [user_message]})

    model = _get_model()
    generation_config = genai.types.GenerationConfig(
        temperature=0.85,
        max_output_tokens=300,
        top_p=0.95,
    )

    try:
        try:
            response = model.generate_content(
                history,
                generation_config=generation_config,
            )
        except google_exceptions.ResourceExhausted as e:
            raise RuntimeError(
                "Gemini quota or rate limit hit for this model (often free tier for "
                "gemini-2.0-flash is exhausted). In backend/.env set "
                "GEMINI_MODEL=gemini-2.5-flash or GEMINI_MODEL=gemini-flash-latest, "
                "restart the server, and see https://ai.google.dev/gemini-api/docs/rate-limits"
            ) from e

        try:
            ai_message = (response.text or "").strip()
        except ValueError as e:
            raise RuntimeError(
                "Gemini returned no text (often blocked by safety settings). "
                "Try a different message or adjust safety in Google AI Studio."
            ) from e

        if not ai_message:
            raise RuntimeError("Gemini returned an empty response.")

        history.append({"role": "model", "parts": [ai_message]})
    except Exception:
        if history and history[-1].get("role") == "user":
            history.pop()
        raise
    return ai_message


def clear_history(session_id: str):
    if session_id in conversations:
        del conversations[session_id]


def parse_emotion(response_text: str) -> tuple[str, str]:
    match = re.match(r"\[(\w+)\]\s*(.*)", response_text, re.DOTALL)
    if match:
        return match.group(1).lower(), match.group(2).strip()
    return "neutral", response_text
