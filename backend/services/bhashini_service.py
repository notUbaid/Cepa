"""
Bhashini Multilingual TTS Service
==================================
National Language Translation Mission (NLTM) — Dhruva Inference API Integration.

Converts CEPA grade announcement text to spoken audio in regional Indian languages,
enabling mandi officers and farmers to receive results in their native language.

**Why this matters:**
85% of India's procurement officers and farmers speak regional languages, not English.
Officers at Nashik/Lasalgaon centres speak Marathi. Kurnool speaks Telugu. Bellary
speaks Kannada. CEPA speaks their language — grade results announced in the officer's
native tongue build trust, reduce transcription disputes, and make the system inclusive.

Research citation:
  [Bhashini-2024] MeitY, Government of India. "Bhashini — National Language Translation
  Mission (NLTM)." API Documentation, 2024. https://bhashini.gov.in
  Dhruva inference API; TTS pipeline; BCP-47 language codes; 22 Indian languages.

Supported languages:
  - Hindi (hi): All-India federal communication
  - Marathi (mr): Nashik / Pimpalgaon / Lasalgaon belt (India's largest onion market)
  - Kannada (kn): Bellary / Hubli / North Karnataka APMCs
  - Telugu (te): Kurnool / Guntur / Hyderabad mandis
  - Tamil (ta): Perambalur / Dindigul onion clusters
  - Gujarati (gu): Mahuva / Bhavnagar producing districts
  - English (en): Fallback for literate officer-facing displays
"""
from __future__ import annotations

import base64
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

BHASHINI_API_ENDPOINT = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
BHASHINI_REQUEST_TIMEOUT_S = 10.0


# ── Language Enum ──────────────────────────────────────────────────────────────

class SupportedLanguage(str, Enum):
    """BCP-47 language codes supported by CEPA's Bhashini integration."""
    HINDI = "hi"
    MARATHI = "mr"
    KANNADA = "kn"
    TELUGU = "te"
    TAMIL = "ta"
    GUJARATI = "gu"
    ENGLISH = "en"


# ── State → Language Mapping ───────────────────────────────────────────────────

_STATE_LANGUAGE_MAP: dict[str, SupportedLanguage] = {
    # Maharashtra (India's #1 onion producing state — Nashik, Pimpalgaon, Lasalgaon)
    "maharashtra": SupportedLanguage.MARATHI,
    "nashik": SupportedLanguage.MARATHI,
    "pimpalgaon": SupportedLanguage.MARATHI,
    "lasalgaon": SupportedLanguage.MARATHI,
    "pune": SupportedLanguage.MARATHI,
    "ahmednagar": SupportedLanguage.MARATHI,
    "solapur": SupportedLanguage.MARATHI,
    # Karnataka (Bellary, Hubli, North Karnataka)
    "karnataka": SupportedLanguage.KANNADA,
    "bellary": SupportedLanguage.KANNADA,
    "hubli": SupportedLanguage.KANNADA,
    "dharwad": SupportedLanguage.KANNADA,
    "bengaluru": SupportedLanguage.KANNADA,
    "bangalore": SupportedLanguage.KANNADA,
    "gadag": SupportedLanguage.KANNADA,
    "haveri": SupportedLanguage.KANNADA,
    # Andhra Pradesh & Telangana (Kurnool, Guntur)
    "andhra": SupportedLanguage.TELUGU,
    "andhra pradesh": SupportedLanguage.TELUGU,
    "telangana": SupportedLanguage.TELUGU,
    "kurnool": SupportedLanguage.TELUGU,
    "guntur": SupportedLanguage.TELUGU,
    "hyderabad": SupportedLanguage.TELUGU,
    # Tamil Nadu
    "tamil nadu": SupportedLanguage.TAMIL,
    "perambalur": SupportedLanguage.TAMIL,
    "dindigul": SupportedLanguage.TAMIL,
    "coimbatore": SupportedLanguage.TAMIL,
    # Gujarat
    "gujarat": SupportedLanguage.GUJARATI,
    "mahuva": SupportedLanguage.GUJARATI,
    "bhavnagar": SupportedLanguage.GUJARATI,
    "rajkot": SupportedLanguage.GUJARATI,
}


def get_language_from_state(state_or_city: str) -> SupportedLanguage:
    """
    Map an Indian state or city name to the primary regional language.

    Args:
        state_or_city: Name of the state, city, or procurement centre location.

    Returns:
        SupportedLanguage for that region. Defaults to HINDI for unmapped regions.
    """
    if not state_or_city:
        return SupportedLanguage.HINDI
    key = state_or_city.strip().lower()
    # Exact match first
    if key in _STATE_LANGUAGE_MAP:
        return _STATE_LANGUAGE_MAP[key]
    # Partial match
    for region, lang in _STATE_LANGUAGE_MAP.items():
        if region in key or key in region:
            return lang
    return SupportedLanguage.HINDI  # Hindi as default for North India / unresolved centres


# ── Recommendation Translations ────────────────────────────────────────────────

_RECOMMENDATION_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ACCEPT_GRADE_A": {
        "hi": "स्वीकृत — ग्रेड A",
        "mr": "मान्य — ग्रेड A",
        "kn": "ಅನುಮೋದಿತ — ದರ್ಜೆ A",
        "te": "అంగీకరించబడింది — గ్రేడ్ A",
        "ta": "ஏற்கப்பட்டது — தரம் A",
        "gu": "સ્વીકૃત — ગ્રેડ A",
        "en": "Accepted — Grade A",
    },
    "ACCEPT_URS": {
        "hi": "स्वीकृत — URS (शिथिल मानक)",
        "mr": "मान्य — URS (शिथिल दर्जा)",
        "kn": "ಅನುಮೋದಿತ — URS (ಶಿಥಿಲ ಮಾನದಂಡ)",
        "te": "అంగీకరించబడింది — URS (సడలింపు ప్రమాణం)",
        "ta": "ஏற்கப்பட்டது — URS (தளர்த்திய தரம்)",
        "gu": "સ્વીકૃત — URS (ઢીલ ધોરણ)",
        "en": "Accepted — URS (Under Relaxed Specs)",
    },
    "REJECT_LOT": {
        "hi": "अस्वीकृत — खेप वापस करें",
        "mr": "नाकारले — माल परत करा",
        "kn": "ತಿರಸ್ಕರಿಸಲಾಗಿದೆ — ಮಾಲನ್ನು ಹಿಂತಿರುಗಿಸಿ",
        "te": "తిరస్కరించబడింది — సరుకు తిరిగి పంపండి",
        "ta": "நிராகரிக்கப்பட்டது — தொகுதியை திருப்பி அனுப்பவும்",
        "gu": "અस्वीकૃત — માલ પાછો આપો",
        "en": "Rejected — Return the lot",
    },
    "ADDITIONAL_SAMPLE_REQUIRED": {
        "hi": "और नमूना चाहिए",
        "mr": "आणखी नमुना हवा",
        "kn": "ಇನ್ನಷ್ಟು ಮಾದರಿ ಬೇಕು",
        "te": "మరిన్ని నమూనాలు అవసరం",
        "ta": "கூடுதல் மாதிரி தேவை",
        "gu": "વધુ નમૂनો જોઈએ",
        "en": "Additional sample required",
    },
}


# ── Grade Announcement Data ────────────────────────────────────────────────────

@dataclass
class GradeAnnouncementLanguage:
    """
    Structured grade announcement payload for TTS synthesis.

    Provides all fields needed to generate a complete spoken grade announcement
    in the target language.
    """
    language: SupportedLanguage
    grade_a_pct: float
    urs_pct: float
    rejected_pct: float
    suspect_count: int          # Bulbs flagged by acoustic/FPI with risk score > 0.6
    lot_recommendation: str     # 'ACCEPT_GRADE_A' | 'ACCEPT_URS' | 'REJECT_LOT' | 'ADDITIONAL_SAMPLE_REQUIRED'
    centre_name: str = ""
    lot_id: str = ""
    total_bulbs: int = 0


# ── Text Templates per Language ────────────────────────────────────────────────

_ANNOUNCEMENT_TEMPLATES: dict[str, str] = {
    "hi": (
        "{centre_clause}लॉट {lot_id_clause}। "
        "ग्रेड A: {grade_a_pct:.0f}%। URS: {urs_pct:.0f}%। "
        "अस्वीकृत: {rejected_pct:.0f}%। "
        "{suspect_clause}"
        "अनुशंसा: {recommendation}।"
    ),
    "mr": (
        "{centre_clause}लॉट {lot_id_clause}। "
        "ग्रेड A: {grade_a_pct:.0f}%। URS: {urs_pct:.0f}%। "
        "नाकारले: {rejected_pct:.0f}%। "
        "{suspect_clause}"
        "शिफारस: {recommendation}।"
    ),
    "kn": (
        "{centre_clause}ಲಾಟ್ {lot_id_clause}. "
        "ದರ್ಜೆ A: {grade_a_pct:.0f}%. URS: {urs_pct:.0f}%. "
        "ತಿರಸ್ಕರಿಸಲಾಗಿದೆ: {rejected_pct:.0f}%. "
        "{suspect_clause}"
        "ಶಿಫಾರಸು: {recommendation}."
    ),
    "te": (
        "{centre_clause}లాట్ {lot_id_clause}. "
        "గ్రేడ్ A: {grade_a_pct:.0f}%. URS: {urs_pct:.0f}%. "
        "తిరస్కరించబడింది: {rejected_pct:.0f}%. "
        "{suspect_clause}"
        "సిఫారసు: {recommendation}."
    ),
    "ta": (
        "{centre_clause}தொகுதி {lot_id_clause}. "
        "தரம் A: {grade_a_pct:.0f}%. URS: {urs_pct:.0f}%. "
        "நிராகரிக்கப்பட்டது: {rejected_pct:.0f}%. "
        "{suspect_clause}"
        "பரிந்துரை: {recommendation}."
    ),
    "gu": (
        "{centre_clause}લૉટ {lot_id_clause}. "
        "ગ્રેડ A: {grade_a_pct:.0f}%. URS: {urs_pct:.0f}%. "
        "અस्वीकૃत: {rejected_pct:.0f}%. "
        "{suspect_clause}"
        "ભलामण: {recommendation}."
    ),
    "en": (
        "{centre_clause}Lot {lot_id_clause}. "
        "Grade A: {grade_a_pct:.0f}%. URS: {urs_pct:.0f}%. "
        "Rejected: {rejected_pct:.0f}%. "
        "{suspect_clause}"
        "Recommendation: {recommendation}."
    ),
}

_SUSPECT_CLAUSE: dict[str, str] = {
    "hi": "{n} बल्ब संदिग्ध — जाँच करें। ",
    "mr": "{n} बल्ब संशयास्पद — तपासणी करा। ",
    "kn": "{n} ಬಲ್ಬ್ ಅನುಮಾನಾಸ್ಪದ — ತನಿಖೆ ಮಾಡಿ. ",
    "te": "{n} బల్బులు అనుమానాస్పదం — తనిఖీ చేయండి. ",
    "ta": "{n} பல்புகள் சந்தேகாஸ்பதம் — சரிபார்க்கவும். ",
    "gu": "{n} બ્લ્બ શંکاس્пد — તপаس кро. ",
    "en": "{n} bulbs suspect — perform cut-open check. ",
}

_CENTRE_CLAUSE: dict[str, str] = {
    "hi": "केंद्र {centre}: ",
    "mr": "केंद्र {centre}: ",
    "kn": "ಕೇಂದ್ರ {centre}: ",
    "te": "కేంద్రం {centre}: ",
    "ta": "மையம் {centre}: ",
    "gu": "кেнদ્р {centre}: ",
    "en": "Centre {centre}: ",
}


def build_grade_announcement_text(announcement: GradeAnnouncementLanguage) -> str:
    """
    Build a complete grade announcement string in the target regional language.

    The announcement covers: centre name, lot ID, Grade A%, URS%, Rejected%,
    suspect bulb count, and the final lot recommendation — all in the target language.

    Args:
        announcement: Structured grade data with language preference.

    Returns:
        Announcement string ready for TTS synthesis or text display.
    """
    lang_code = announcement.language.value
    template = _ANNOUNCEMENT_TEMPLATES.get(lang_code, _ANNOUNCEMENT_TEMPLATES["en"])

    # Centre clause
    if announcement.centre_name:
        centre_tmpl = _CENTRE_CLAUSE.get(lang_code, _CENTRE_CLAUSE["en"])
        centre_clause = centre_tmpl.format(centre=announcement.centre_name)
    else:
        centre_clause = ""

    # Lot ID clause
    lot_id_clause = announcement.lot_id if announcement.lot_id else "—"

    # Suspect clause
    if announcement.suspect_count > 0:
        suspect_tmpl = _SUSPECT_CLAUSE.get(lang_code, _SUSPECT_CLAUSE["en"])
        suspect_clause = suspect_tmpl.format(n=announcement.suspect_count)
    else:
        suspect_clause = ""

    # Recommendation translation
    rec_map = _RECOMMENDATION_TRANSLATIONS.get(
        announcement.lot_recommendation,
        _RECOMMENDATION_TRANSLATIONS["REJECT_LOT"],
    )
    recommendation = rec_map.get(lang_code, rec_map["en"])

    return template.format(
        centre_clause=centre_clause,
        lot_id_clause=lot_id_clause,
        grade_a_pct=announcement.grade_a_pct,
        urs_pct=announcement.urs_pct,
        rejected_pct=announcement.rejected_pct,
        suspect_clause=suspect_clause,
        recommendation=recommendation,
    )


# ── TTS Result ─────────────────────────────────────────────────────────────────

@dataclass
class BhashiniTTSResult:
    """Result of a Bhashini TTS synthesis request."""
    audio_bytes: bytes | None
    content_type: str           # 'audio/wav' | 'audio/mp3'
    language: SupportedLanguage
    announcement_text: str
    success: bool
    error_message: str
    is_mock: bool
    latency_ms: float


# ── TTS Synthesis ──────────────────────────────────────────────────────────────

def synthesize_grade_announcement(
    announcement: GradeAnnouncementLanguage,
    bhashini_api_key: str = "",
) -> BhashiniTTSResult:
    """
    Synthesize a grade announcement to speech via Bhashini Dhruva TTS API.

    When no API key is configured, returns a text-only result (is_mock=True,
    success=False) with the full announcement text still populated — callers
    can display or log the text even without audio synthesis.

    Args:
        announcement: Grade result data with language preference.
        bhashini_api_key: Bhashini API key (from BHASHINI_API_KEY env var).
                          If empty, text-only fallback is returned.

    Returns:
        BhashiniTTSResult with audio_bytes if synthesis succeeded.
    """
    t_start = time.perf_counter()
    text = build_grade_announcement_text(announcement)
    lang = announcement.language

    if not bhashini_api_key:
        logger.info(
            "Bhashini API key not configured — returning text-only announcement (%s, %d chars)",
            lang.value, len(text),
        )
        return BhashiniTTSResult(
            audio_bytes=None,
            content_type="text/plain",
            language=lang,
            announcement_text=text,
            success=False,
            error_message=(
                "Bhashini API key not configured. "
                "Set BHASHINI_API_KEY in .env to enable voice synthesis. "
                "Text announcement is available in the response."
            ),
            is_mock=True,
            latency_ms=round((time.perf_counter() - t_start) * 1000, 1),
        )

    # Build Dhruva TTS pipeline payload
    payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {"sourceLanguage": lang.value},
                    "gender": "female",
                    "samplingRate": 8000,
                },
            }
        ],
        "inputData": {
            "input": [{"source": text}]
        },
    }

    try:
        req = urllib.request.Request(
            BHASHINI_API_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": bhashini_api_key,
                "Content-Type": "application/json",
                "User-Agent": "Cepa-Mandi-AI/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=BHASHINI_REQUEST_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        # Parse response: pipelineResponse[0].audio[0].audioContent (base64 WAV)
        audio_b64 = body["pipelineResponse"][0]["audio"][0]["audioContent"]
        audio_bytes = base64.b64decode(audio_b64)

        latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
        logger.info(
            "Bhashini TTS success: lang=%s text_len=%d audio_bytes=%d latency=%.0fms",
            lang.value, len(text), len(audio_bytes), latency_ms,
        )
        return BhashiniTTSResult(
            audio_bytes=audio_bytes,
            content_type="audio/wav",
            language=lang,
            announcement_text=text,
            success=True,
            error_message="",
            is_mock=False,
            latency_ms=latency_ms,
        )

    except Exception as exc:
        latency_ms = round((time.perf_counter() - t_start) * 1000, 1)
        logger.warning("Bhashini TTS failed (%s): %s", lang.value, exc)
        return BhashiniTTSResult(
            audio_bytes=None,
            content_type="text/plain",
            language=lang,
            announcement_text=text,
            success=False,
            error_message=str(exc),
            is_mock=True,
            latency_ms=latency_ms,
        )


# ── Convenience: build from inspection stats ───────────────────────────────────

def build_announcement_from_inspection(
    *,
    grade_a_pct: float,
    urs_pct: float,
    rejected_pct: float,
    lot_recommendation: str,
    suspect_count: int = 0,
    centre_name: str = "",
    lot_id: str = "",
    total_bulbs: int = 0,
    state_or_city: str = "",
    language: SupportedLanguage | None = None,
) -> GradeAnnouncementLanguage:
    """
    Convenience builder: create a GradeAnnouncementLanguage from inspection stats.

    Automatically infers language from state_or_city if language is not explicitly provided.

    Args:
        grade_a_pct: Percentage of Grade A bulbs (0–100).
        urs_pct: Percentage of URS bulbs (0–100).
        rejected_pct: Percentage of rejected bulbs (0–100).
        lot_recommendation: Decision code from grading engine.
        suspect_count: Number of bulbs flagged by acoustic/FPI risk score > 0.6.
        centre_name: Name of the procurement centre.
        lot_id: Lot / consignment ID.
        total_bulbs: Total bulbs in sample.
        state_or_city: State or city for language inference.
        language: Explicit language override.

    Returns:
        GradeAnnouncementLanguage ready for synthesize_grade_announcement().
    """
    if language is None:
        language = get_language_from_state(state_or_city)

    return GradeAnnouncementLanguage(
        language=language,
        grade_a_pct=grade_a_pct,
        urs_pct=urs_pct,
        rejected_pct=rejected_pct,
        suspect_count=suspect_count,
        lot_recommendation=lot_recommendation,
        centre_name=centre_name,
        lot_id=lot_id,
        total_bulbs=total_bulbs,
    )
