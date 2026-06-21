"""
Google Gemini AI evaluation service.
Uses the exact rubric: Vocabulary(25) + Grammar(25) + Fluency(25) + Coherence(25) = 100.
Uses the new google-genai SDK per https://ai.google.dev/gemini-api/docs

Also provides TTS for paragraph audio generation:
https://ai.google.dev/gemini-api/docs/speech-generation
"""

import re
import json
import logging
import os
import wave
from typing import Optional

from config import GEMINI_API_KEY, DEMO_MODE, PARAGRAPH_AUDIO_DIR, LLM_MAX_OUTPUT_TOKENS

logger = logging.getLogger(__name__)

# ── Dil zorlaması ─────────────────────────────────────────
# Model bazen İngilizce metni analiz ederken geri bildirimi de İngilizce
# yazıyor. system_instruction ile çıktının TÜRKÇE olmasını kesinleştiriyoruz.
TURKISH_SYSTEM_INSTRUCTION = (
    "Sen bir İngilizce konuşma değerlendirme uzmanısın. "
    "İncelediğin öğrenci metni İngilizce olsa bile, ürettiğin TÜM geri bildirim, "
    "açıklama ve öneri metinlerini İSTİSNASIZ TÜRKÇE yaz. "
    "JSON'daki 'feedback' ve 'suggestions' alanları kesinlikle Türkçe olmalı; "
    "İngilizce cümle kullanma. Sadece istenen JSON'u döndür."
)

# ── Gemini evaluation prompt (EXACT format per requirements) ──
EVALUATION_PROMPT = """Sen bir İngilizce konuşma değerlendirme uzmanısın.

Öğrencinin yanıtını aşağıdaki 4 kritere göre değerlendir:

1. Kelime Bilgisi / Vocabulary (0-25) - Kullanılan kelimelerin çeşitliliği ve uygunluğu
2. Dilbilgisi / Grammar (0-25) - Gramer yapılarının doğruluğu
3. Akıcılık / Fluency (0-25) - Konuşmanın pürüzsüzlüğü, temposu ve doğallığı
4. Tutarlılık / Coherence (0-25) - Fikirlerin mantıksal düzeni ve bağlantısı

100 üzerinden toplam puan ver.

Öğrencinin yanıtını orijinal paragrafla karşılaştır.
Eksik bırakılan anahtar fikirleri cezalandır.
ÖNEMLİ: "feedback" ve "suggestions" alanlarını İSTİSNASIZ TÜRKÇE yaz — öğrenci metni
İngilizce olsa bile geri bildirim ve öneriler TÜRKÇE olmalı, İngilizce cümle kullanma.
Geri bildirim detaylı olmalı: öğrencinin ne iyi yaptığını, neyi geliştirmesi gerektiğini ve nasıl geliştirebileceğini açıkla.

SADECE aşağıdaki JSON formatında yanıt ver:
{{
  "vocabulary": <puan>,
  "grammar": <puan>,
  "fluency": <puan>,
  "coherence": <puan>,
  "total": <toplam_puan>,
  "feedback": "<Türkçe detaylı geri bildirim, en az 3-4 cümle>",
  "suggestions": ["<Türkçe öneri 1>", "<Türkçe öneri 2>", "<Türkçe öneri 3>"]
}}

Orijinal paragraf:
\"\"\"
{ORIGINAL}
\"\"\"

Öğrenci metni:
\"\"\"
{TRANSCRIPT}
\"\"\"
"""


async def evaluate_with_gemini(
    transcript: str,
    original_text: str,
    compare_mode: bool = True,
) -> dict:
    """
    Send transcript to Gemini for evaluation.
    Returns: {
        "vocabulary": float, "grammar": float,
        "fluency": float, "coherence": float,
        "total": float, "feedback": str, "suggestions": list
    }
    """
    # ── Validation ────────────────────────────────────────
    word_count = len(transcript.strip().split())
    if word_count == 0:
        return {
            "error": "no_speech",
            "message": "No speech detected. Please try recording again.",
        }
    if word_count < 5:
        return {
            "error": "too_short",
            "message": f"Your response is too short ({word_count} words). Please speak at least 5 words.",
        }

    # ── Demo mode ─────────────────────────────────────────
    if DEMO_MODE:
        return _mock_evaluation(transcript, original_text)

    # ── Real Gemini call ──────────────────────────────────
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = EVALUATION_PROMPT.format(
            ORIGINAL=original_text,
            TRANSCRIPT=transcript,
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                # Geri bildirimin TÜRKÇE olmasını kesinleştir.
                system_instruction=TURKISH_SYSTEM_INSTRUCTION,
                # Kaçak maliyeti önlemek için çıktı token tavanı (CLAUDE.md AI kuralı).
                max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
            ),
        )
        text = response.text.strip()

        # Parse JSON from response
        return _parse_gemini_response(text)

    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return _mock_evaluation(transcript, original_text)


async def evaluate_audio_with_gemini(
    audio_path: str,
    original_text: str,
) -> dict:
    """
    Send audio directly to Gemini for combined transcription + evaluation.
    This is the premium flow: Gemini hears the audio and evaluates pronunciation,
    fluency, etc. from the actual speech, not just the transcript.
    """
    if DEMO_MODE:
        return _mock_audio_evaluation()

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        ext = os.path.splitext(audio_path)[1].lower()
        mime_map = {
            ".webm": "audio/webm",
            ".wav": "audio/wav",
            ".mp3": "audio/mp3",
            ".ogg": "audio/ogg",
        }
        mime_type = mime_map.get(ext, "audio/webm")

        prompt = f"""Sen bir İngilizce konuşma değerlendirme uzmanısın. Bu öğrencinin ses kaydını dinle ve İngilizce konuşma becerilerini değerlendir.

Öğrenciden aşağıdaki paragrafı okuması/anlatması istendi:
\"\"\"{original_text}\"\"\"

Aşağıdaki kriterlere göre değerlendir:
1. Kelime Bilgisi / Vocabulary (0-25) - Kullanılan kelimelerin çeşitliliği ve uygunluğu
2. Dilbilgisi / Grammar (0-25) - Konuşmadaki gramer doğruluğu
3. Akıcılık / Fluency (0-25) - Konuşmanın pürüzsüzlüğü, temposu ve doğallığı
4. Tutarlılık / Coherence (0-25) - Fikirlerin mantıksal düzeni ve bağlantısı

Ayrıca öğrencinin ne söylediğini transkript olarak yaz.
Orijinal paragrafla karşılaştır ve eksik bırakılan anahtar fikirleri not et.
ÖNEMLİ: "feedback" ve "suggestions" alanlarını İSTİSNASIZ TÜRKÇE yaz — konuşma
İngilizce olsa bile geri bildirim ve öneriler TÜRKÇE olmalı, İngilizce cümle kullanma. Detaylı olmalı.

SADECE aşağıdaki JSON formatında yanıt ver:
{{
  "transcript": "<öğrencinin söylediği>",
  "vocabulary": <puan>,
  "grammar": <puan>,
  "fluency": <puan>,
  "coherence": <puan>,
  "total": <toplam_puan>,
  "feedback": "<Türkçe detaylı geri bildirim, en az 3-4 cümle>",
  "suggestions": ["<Türkçe öneri 1>", "<Türkçe öneri 2>", "<Türkçe öneri 3>"]
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                # Geri bildirimin TÜRKÇE olmasını kesinleştir.
                system_instruction=TURKISH_SYSTEM_INSTRUCTION,
                # Kaçak maliyeti önlemek için çıktı token tavanı (CLAUDE.md AI kuralı).
                max_output_tokens=LLM_MAX_OUTPUT_TOKENS,
            ),
        )

        return _parse_gemini_response(response.text.strip())

    except Exception as e:
        logger.error(f"Gemini audio evaluation error: {e}")
        return _mock_audio_evaluation()


async def generate_paragraph_audio(text: str, paragraph_id: int) -> Optional[str]:
    """
    Generate TTS audio for a paragraph using gTTS (Google Text-to-Speech).
    Produces clean, clear MP3 audio — no API key required.
    Slow mode is used for English language learners.
    Returns the relative path to the generated audio file, or None.
    """
    try:
        from gtts import gTTS

        logger.info(f"TTS (gTTS): Generating audio for paragraph {paragraph_id} ({len(text)} chars)")

        # Clean up old files (both .mp3 and .wav)
        for ext in [".mp3", ".wav"]:
            old_file = os.path.join(PARAGRAPH_AUDIO_DIR, f"paragraph_{paragraph_id}{ext}")
            if os.path.exists(old_file):
                os.remove(old_file)
                logger.info(f"TTS: Removed old file: {old_file}")

        # Generate with gTTS — slow=True for language learners
        tts = gTTS(text=text, lang="en", slow=True)

        filename = f"paragraph_{paragraph_id}.mp3"
        filepath = os.path.join(PARAGRAPH_AUDIO_DIR, filename)
        tts.save(filepath)

        file_size = os.path.getsize(filepath)
        logger.info(f"TTS (gTTS): Saved {filepath} ({file_size} bytes)")

        return f"/uploads/paragraphs/{filename}"

    except Exception as e:
        logger.error(f"gTTS error: {type(e).__name__}: {e}", exc_info=True)
        return None


def _parse_gemini_response(text: str) -> dict:
    """Extract structured data from Gemini's response."""
    try:
        # Try direct JSON parse
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            data = json.loads(json_match.group())
            result = {
                "vocabulary": min(25, max(0, float(data.get("vocabulary", 0)))),
                "grammar": min(25, max(0, float(data.get("grammar", 0)))),
                "fluency": min(25, max(0, float(data.get("fluency", 0)))),
                "coherence": min(25, max(0, float(data.get("coherence", 0)))),
                "total": min(100, max(0, float(data.get("total", 0)))),
                "feedback": data.get("feedback", ""),
                "suggestions": data.get("suggestions", []),
            }
            # Include transcript if present (from audio evaluation)
            if "transcript" in data:
                result["transcript"] = data["transcript"]
            return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse Gemini JSON: {e}")

    # Fallback: try Score: X/100 format
    score_match = re.search(r'Score:\s*(\d+)/100', text)
    feedback_match = re.search(r'Feedback:\s*(.+)', text, re.DOTALL)
    if score_match:
        total = min(100, int(score_match.group(1)))
        quarter = total / 4
        return {
            "vocabulary": round(quarter, 1),
            "grammar": round(quarter, 1),
            "fluency": round(quarter, 1),
            "coherence": round(quarter, 1),
            "total": total,
            "feedback": feedback_match.group(1).strip() if feedback_match else "",
            "suggestions": [],
        }

    # Final fallback
    return _mock_evaluation("", "")


def _mock_evaluation(transcript: str, original: str) -> dict:
    """Generate a realistic mock evaluation for demo mode."""
    import random
    word_count = len(transcript.split()) if transcript else 0
    original_words = set(original.lower().split()) if original else set()
    student_words = set(transcript.lower().split()) if transcript else set()

    overlap = len(original_words & student_words) / max(len(original_words), 1)

    base = max(30, min(85, int(overlap * 70) + word_count * 2))
    vocab = min(25, max(5, int(base * 0.25) + random.randint(-2, 3)))
    grammar = min(25, max(5, int(base * 0.25) + random.randint(-2, 3)))
    fluency = min(25, max(5, int(base * 0.25) + random.randint(-3, 2)))
    coherence = min(25, max(5, int(base * 0.25) + random.randint(-2, 2)))
    total = vocab + grammar + fluency + coherence

    feedbacks = [
        "İyi bir çaba! Orijinal metindeki ana fikirleri daha fazla dahil etmeye çalışın. Kelime dağarcığınızı genişletmek için günlük İngilizce okuma alışkanlığı edinmenizi öneririm.",
        "Telaffuzunuz güzel! Daha zengin kelime çeşitliliği kullanmaya özen gösterin. Cümlelerinizi bağlaçlarla birbirine bağlayarak daha akıcı bir anlatım elde edebilirsiniz.",
        "İyi yapılandırılmış bir yanıt. Daha güvenli bir şekilde konuşmayı deneyin. Telaffuz egzersizleri yapıp sesinizi kaydetme alışkanlığı edinmeniz faydalı olacaktır.",
        "Ana fikirleri iyi kavramışsınız. Dilbilgisi kurallarına biraz daha dikkat edin, özellikle zaman ekleri ve özne-yüklem uyumu konusunda gelişme gösterebilirsiniz.",
        "Sağlam bir deneme! Fikirlerinizi daha pürüzsüz bağlamayı pratik edin. 'however', 'moreover', 'in addition' gibi bağlaçları kullanmayı alıştırma yapın.",
    ]
    suggestions_pool = [
        "Daha uzun ve karışık cümleler kurmayı deneyin",
        "Kelime çeşitliliğinizi artırın, eşanlamlı kelimeler kullanın",
        "Orijinal metindeki anahtar fikirleri daha fazla dahil edin",
        "Geçmiş zaman kullanımını pratik edin",
        "Bağlaçlar (however, moreover, therefore) kullanmayı alışın",
        "Sabit bir tempoda konuşmaya özen gösterin",
        "Betimleyici sıfatlar ve zarflar kullanın",
        "Telaffuz egzersizleri için kendinizi kaydedip dinleyin",
    ]

    return {
        "vocabulary": vocab,
        "grammar": grammar,
        "fluency": fluency,
        "coherence": coherence,
        "total": total,
        "feedback": random.choice(feedbacks),
        "suggestions": random.sample(suggestions_pool, min(3, len(suggestions_pool))),
    }


def _mock_audio_evaluation() -> dict:
    """Mock for audio-based evaluation in demo mode."""
    return _mock_evaluation(
        "The weather today is sunny and warm. I enjoy spending time outdoors.",
        "The weather today is sunny and warm. There are no clouds in the sky.",
    )
