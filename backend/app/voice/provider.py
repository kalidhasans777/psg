"""
MEDORA Tamil-First Voice Assistant & Speech Provider Abstraction
Supports Google Cloud Speech-to-Text, Microsoft Azure AI Speech, and Browser Web Speech API fallback.
Never simulates speech recognition with hardcoded transcripts.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import base64
import httpx

from app.ai.terminology import extract_medical_terms
from app.config import get_settings

settings = get_settings()

TAMIL_ASSISTANT_PROMPTS = {
    0: {
        "ta": "வணக்கம்! உங்களுக்கு என்ன உடல்நலப் பிரச்சனை இருக்கிறது? உங்கள் அறிகுறிகளைச் சொல்லுங்கள்.",
        "en": "Hello! What health problem are you experiencing today? Please describe your symptoms.",
        "field": "symptoms",
    },
    1: {
        "ta": "இந்த அறிகுறிகள் எத்தனை நாட்களாக இருக்கின்றன? வேறு ஏதாவது பிரச்சனை அல்லது சோர்வு இருக்கிறதா?",
        "en": "How many days have you had these symptoms? Do you have any additional discomfort or fatigue?",
        "field": "duration_and_additional",
    },
    2: {
        "ta": "நீங்கள் இதற்காக ஏதாவது மாத்திரை அல்லது மருந்து எடுத்துக்கொண்டீர்களா?",
        "en": "Have you taken any tablets or medications for this so far?",
        "field": "medications",
    },
    3: {
        "ta": "சரி. நீங்கள் சொன்ன விவரங்களை இப்போது காட்டுகிறேன். சரியாக இருக்கிறதா என்று பார்த்து உறுதிப்படுத்துங்கள்.",
        "en": "Thank you. I am displaying the details you shared below. Please review, edit if needed, and confirm.",
        "field": "confirm",
    },
}


class SpeechProviderBase(ABC):
    provider_name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str, language: str) -> Dict[str, Any]:
        ...


class GoogleCloudSpeechProvider(SpeechProviderBase):
    provider_name = "google_cloud_speech"

    def is_configured(self) -> bool:
        return bool(settings.GOOGLE_CLOUD_SPEECH_API_KEY)

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str, language: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "success": False,
                "provider": self.provider_name,
                "configured": False,
                "error": "GOOGLE_CLOUD_SPEECH_API_KEY is not configured.",
            }
        lang_code = "ta-IN" if language.startswith("ta") else "en-IN"
        alt_langs = ["en-IN"] if lang_code == "ta-IN" else ["ta-IN"]
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={settings.GOOGLE_CLOUD_SPEECH_API_KEY}"
        payload = {
            "config": {
                "languageCode": lang_code,
                "alternativeLanguageCodes": alt_langs,
                "enableAutomaticPunctuation": True,
                "model": "default",
            },
            "audio": {"content": audio_b64},
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results", [])
            transcript = " ".join(
                r["alternatives"][0]["transcript"]
                for r in results
                if r.get("alternatives")
            ).strip()
            confidence = (
                results[0]["alternatives"][0].get("confidence")
                if results and results[0].get("alternatives")
                else None
            )
            return {
                "success": True,
                "provider": self.provider_name,
                "configured": True,
                "language": lang_code,
                "transcript": transcript,
                "confidence": confidence,
            }
        except Exception as exc:
            return {
                "success": False,
                "provider": self.provider_name,
                "configured": True,
                "error": f"Google Cloud Speech transcription failed: {exc}",
            }


class AzureSpeechProvider(SpeechProviderBase):
    provider_name = "azure_ai_speech"

    def is_configured(self) -> bool:
        return bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION)

    async def transcribe_audio(self, audio_bytes: bytes, mime_type: str, language: str) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "success": False,
                "provider": self.provider_name,
                "configured": False,
                "error": "AZURE_SPEECH_KEY or AZURE_SPEECH_REGION is not configured.",
            }
        lang_code = "ta-IN" if language.startswith("ta") else "en-IN"
        endpoint = (
            f"https://{settings.AZURE_SPEECH_REGION}.stt.speech.microsoft.com/"
            f"speech/recognition/conversation/cognitiveservices/v1?language={lang_code}"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY,
            "Content-Type": mime_type or "audio/wav",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(endpoint, headers=headers, content=audio_bytes)
                resp.raise_for_status()
                data = resp.json()
            return {
                "success": data.get("RecognitionStatus") == "Success",
                "provider": self.provider_name,
                "configured": True,
                "language": lang_code,
                "transcript": data.get("DisplayText", ""),
                "raw_status": data.get("RecognitionStatus"),
            }
        except Exception as exc:
            return {
                "success": False,
                "provider": self.provider_name,
                "configured": True,
                "error": f"Azure Speech transcription failed: {exc}",
            }


def get_active_speech_provider() -> Optional[SpeechProviderBase]:
    pref = settings.VOICE_PROVIDER.lower()
    google = GoogleCloudSpeechProvider()
    azure = AzureSpeechProvider()

    if pref == "google_cloud" and google.is_configured():
        return google
    if pref == "azure" and azure.is_configured():
        return azure
    if pref == "auto":
        if google.is_configured():
            return google
        if azure.is_configured():
            return azure
    return None


def get_voice_capabilities() -> Dict[str, Any]:
    google = GoogleCloudSpeechProvider()
    azure = AzureSpeechProvider()
    active = get_active_speech_provider()
    return {
        "active_cloud_provider": active.provider_name if active else None,
        "google_cloud_configured": google.is_configured(),
        "azure_configured": azure.is_configured(),
        "browser_webspeech_supported": True,
        "supported_languages": ["ta-IN", "en-IN", "ta-EN-mixed"],
        "note": (
            f"Cloud STT active ({active.provider_name})."
            if active
            else "No cloud STT API key configured; live microphone recognition runs via Browser Web Speech API (ta-IN / en-IN) with manual text correction fallback."
        ),
    }


def process_voice_assistant_turn(
    language: str,
    step: int,
    patient_utterance: str,
    collected_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Guided Tamil-first multi-turn healthcare voice assistant state machine."""
    is_tamil = language.startswith("ta") or language == "mixed"
    lang_key = "ta" if is_tamil else "en"

    updated = dict(collected_data or {})
    cleaned = (patient_utterance or "").strip()

    if cleaned:
        terms = extract_medical_terms(cleaned)
        if step == 0:
            updated["raw_symptoms_statement"] = cleaned
            updated["detected_terms"] = terms
            if terms.get("detected_duration") and not updated.get("duration"):
                updated["duration"] = terms["detected_duration"]
        elif step == 1:
            updated["duration_and_additional"] = cleaned
            if terms.get("detected_duration"):
                updated["duration"] = terms["detected_duration"]
        elif step == 2:
            updated["medications"] = "No medication reported" if terms.get("no_medication_cue") else cleaned

    # Advance step cleanly
    if not cleaned and step == 0:
        next_step = 0
    else:
        next_step = min(step + 1, 3)

    # Smart skip if patient already answered duration in step 0
    prompt_obj = TAMIL_ASSISTANT_PROMPTS[next_step]
    prompt_text = prompt_obj[lang_key]

    # Dynamic confirmation question in Tamil if duration was detected at step 0
    if next_step == 1 and updated.get("duration") and is_tamil:
        prompt_text = f"இந்த அறிகுறிகள் {updated['duration']} ஆக இருக்கிறதா? வேறு ஏதாவது பிரச்சனை அல்லது சோர்வு இருக்கிறதா?"

    combined_transcript = " ".join(
        part
        for part in [
            updated.get("raw_symptoms_statement", ""),
            updated.get("duration_and_additional", ""),
            (f"Medication: {updated.get('medications')}" if updated.get("medications") else ""),
        ]
        if part
    ).strip()

    return {
        "current_step": next_step,
        "completed": next_step >= 3,
        "assistant_prompt_ta": prompt_obj["ta"] if next_step != 1 else prompt_text,
        "assistant_prompt_en": prompt_obj["en"],
        "assistant_prompt": prompt_text,
        "tts_language": "ta-IN" if is_tamil else "en-IN",
        "collected_data": updated,
        "combined_transcript": combined_transcript,
        "extracted_terminology": extract_medical_terms(combined_transcript),
    }
