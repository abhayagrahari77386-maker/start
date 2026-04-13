"""
OpenAI GPT-4o Service — The brain of the avatar.
Generates human-like conversational responses with emotion tags.
"""

from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL, SYSTEM_PROMPT


client = OpenAI(api_key=OPENAI_API_KEY)

# In-memory conversation history per session
conversations: dict[str, list] = {}


def get_or_create_history(session_id: str) -> list:
    """Get conversation history for a session, or create a new one."""
    if session_id not in conversations:
        conversations[session_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    return conversations[session_id]


async def generate_response(session_id: str, user_message: str) -> str:
    """
    Send user message to GPT-4o and get a human-like response.
    Returns the AI response text (with emotion tag).
    """
    history = get_or_create_history(session_id)

    # Add user message to history
    history.append({"role": "user", "content": user_message})

    # Keep history manageable (last 20 messages + system prompt)
    if len(history) > 21:
        history = [history[0]] + history[-20:]
        conversations[session_id] = history

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=history,
        temperature=0.85,
        max_tokens=300,
        top_p=0.95,
        frequency_penalty=0.3,
        presence_penalty=0.4,
    )

    ai_message = response.choices[0].message.content.strip()

    # Add AI response to history
    history.append({"role": "assistant", "content": ai_message})

    return ai_message


def clear_history(session_id: str):
    """Clear conversation history for a session."""
    if session_id in conversations:
        del conversations[session_id]


def parse_emotion(response_text: str) -> tuple[str, str]:
    """
    Parse emotion tag from response.
    Returns (emotion, clean_text).
    Example: "[happy] That's great!" → ("happy", "That's great!")
    """
    import re
    match = re.match(r'\[(\w+)\]\s*(.*)', response_text, re.DOTALL)
    if match:
        return match.group(1).lower(), match.group(2).strip()
    return "neutral", response_text
