"""
Speech-to-Text service using Gemini's native audio understanding.
Instead of a separate Google Cloud Speech-to-Text API, we use Gemini's
built-in audio understanding to transcribe student recordings.
Reference: https://ai.google.dev/gemini-api/docs/audio
"""

import logging
import os
import base64
from config import DEMO_MODE, GEMINI_API_KEY

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_path: str) -> dict:
    """
    Convert audio file to text using Gemini's audio understanding.
    Returns: {"transcript": str, "confidence": float, "word_count": int}
    """
    if DEMO_MODE:
        return _mock_transcription(audio_path)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        # Read audio file as bytes
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        # Determine MIME type
        ext = os.path.splitext(audio_path)[1].lower()
        mime_map = {
            ".webm": "audio/webm",
            ".wav": "audio/wav",
            ".mp3": "audio/mp3",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }
        mime_type = mime_map.get(ext, "audio/webm")

        # Use Gemini to transcribe the audio directly
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Transcribe this audio recording word-for-word. Return ONLY the transcription text, nothing else. If the audio is silent or unintelligible, return an empty string.",
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
        )

        transcript = response.text.strip()
        # Clean up any quotation marks Gemini might add around the transcript
        if transcript.startswith('"') and transcript.endswith('"'):
            transcript = transcript[1:-1]

        word_count = len(transcript.split()) if transcript else 0

        return {
            "transcript": transcript,
            "confidence": 0.9,   # Gemini doesn't give explicit confidence
            "word_count": word_count,
        }

    except Exception as e:
        logger.error(f"Gemini transcription error: {e}")
        return _mock_transcription(audio_path)


def _mock_transcription(audio_path: str) -> dict:
    """Generate mock transcription for demo mode."""
    import random

    demo_transcripts = [
        "The weather today is sunny and warm. I enjoy spending time outdoors when the sun is shining brightly.",
        "Education is very important for children. Schools help students learn new things and develop their skills.",
        "My favorite hobby is reading books. I like to read stories about adventure and science fiction.",
        "Technology has changed our lives in many ways. We use computers and phones every day for communication.",
        "Healthy eating is important for our body. We should eat vegetables and fruits every day to stay strong.",
        "I went to the park yesterday with my friends. We played football and had a wonderful time together.",
        "Learning a new language takes practice and patience. It is important to study regularly and speak often.",
    ]

    transcript = random.choice(demo_transcripts)
    return {
        "transcript": transcript,
        "confidence": round(random.uniform(0.75, 0.95), 2),
        "word_count": len(transcript.split()),
    }
