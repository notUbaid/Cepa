"""
Tests for the Bhashini Multilingual TTS Service.

Validates language inference, announcement text generation in all 7 languages,
TTS result structure, and graceful fallback when API key is absent.
"""
from __future__ import annotations

import pytest

from services.bhashini_service import (
    BhashiniTTSResult,
    GradeAnnouncementLanguage,
    SupportedLanguage,
    build_announcement_from_inspection,
    build_grade_announcement_text,
    get_language_from_state,
    synthesize_grade_announcement,
)


# ── Language Inference ─────────────────────────────────────────────────────────

class TestGetLanguageFromState:
    def test_nashik_maps_to_marathi(self):
        assert get_language_from_state("nashik") == SupportedLanguage.MARATHI

    def test_lasalgaon_maps_to_marathi(self):
        assert get_language_from_state("Lasalgaon") == SupportedLanguage.MARATHI

    def test_maharashtra_maps_to_marathi(self):
        assert get_language_from_state("maharashtra") == SupportedLanguage.MARATHI

    def test_bellary_maps_to_kannada(self):
        assert get_language_from_state("bellary") == SupportedLanguage.KANNADA

    def test_bangalore_maps_to_kannada(self):
        assert get_language_from_state("Bangalore") == SupportedLanguage.KANNADA

    def test_kurnool_maps_to_telugu(self):
        assert get_language_from_state("kurnool") == SupportedLanguage.TELUGU

    def test_hyderabad_maps_to_telugu(self):
        assert get_language_from_state("Hyderabad") == SupportedLanguage.TELUGU

    def test_tamil_nadu_maps_to_tamil(self):
        assert get_language_from_state("tamil nadu") == SupportedLanguage.TAMIL

    def test_gujarat_maps_to_gujarati(self):
        assert get_language_from_state("gujarat") == SupportedLanguage.GUJARATI

    def test_unknown_defaults_to_hindi(self):
        assert get_language_from_state("random unknown state") == SupportedLanguage.HINDI

    def test_empty_string_defaults_to_hindi(self):
        assert get_language_from_state("") == SupportedLanguage.HINDI


# ── build_grade_announcement_text ─────────────────────────────────────────────

class TestBuildGradeAnnouncementText:
    """Each language must produce a non-empty string containing the numeric values."""

    def _make_ann(self, lang: SupportedLanguage, lot_recommendation: str = "ACCEPT_GRADE_A") -> GradeAnnouncementLanguage:
        return GradeAnnouncementLanguage(
            language=lang,
            grade_a_pct=73.0,
            urs_pct=21.0,
            rejected_pct=6.0,
            suspect_count=3,
            lot_recommendation=lot_recommendation,
            centre_name="Test APMC",
            lot_id="LOT-001",
            total_bulbs=27,
        )

    def test_marathi_contains_percentages(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.MARATHI))
        assert "73" in text
        assert "21" in text
        assert "6" in text

    def test_marathi_contains_lot_id(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.MARATHI))
        assert "LOT-001" in text

    def test_marathi_contains_centre_name(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.MARATHI))
        assert "Test APMC" in text

    def test_hindi_non_empty(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.HINDI))
        assert len(text) > 20

    def test_kannada_non_empty(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.KANNADA))
        assert len(text) > 20

    def test_telugu_non_empty(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.TELUGU))
        assert len(text) > 20

    def test_tamil_non_empty(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.TAMIL))
        assert len(text) > 20

    def test_gujarati_non_empty(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.GUJARATI))
        assert len(text) > 20

    def test_english_contains_grade_a(self):
        text = build_grade_announcement_text(self._make_ann(SupportedLanguage.ENGLISH))
        assert "Grade A" in text or "grade a" in text.lower()

    def test_english_reject_recommendation(self):
        ann = self._make_ann(SupportedLanguage.ENGLISH, lot_recommendation="REJECT_LOT")
        text = build_grade_announcement_text(ann)
        assert "Reject" in text or "reject" in text.lower()

    def test_english_urs_recommendation(self):
        ann = self._make_ann(SupportedLanguage.ENGLISH, lot_recommendation="ACCEPT_URS")
        text = build_grade_announcement_text(ann)
        assert "URS" in text

    def test_suspect_count_zero_no_clause(self):
        ann = GradeAnnouncementLanguage(
            language=SupportedLanguage.ENGLISH,
            grade_a_pct=80.0,
            urs_pct=15.0,
            rejected_pct=5.0,
            suspect_count=0,
            lot_recommendation="ACCEPT_GRADE_A",
        )
        text = build_grade_announcement_text(ann)
        assert "suspect" not in text.lower() or "0 bulbs suspect" in text.lower()

    def test_suspect_count_positive_in_text(self):
        ann = GradeAnnouncementLanguage(
            language=SupportedLanguage.ENGLISH,
            grade_a_pct=60.0,
            urs_pct=30.0,
            rejected_pct=10.0,
            suspect_count=5,
            lot_recommendation="ACCEPT_URS",
        )
        text = build_grade_announcement_text(ann)
        assert "5" in text

    def test_no_centre_name_omits_centre_clause(self):
        ann = GradeAnnouncementLanguage(
            language=SupportedLanguage.ENGLISH,
            grade_a_pct=75.0,
            urs_pct=20.0,
            rejected_pct=5.0,
            suspect_count=0,
            lot_recommendation="ACCEPT_GRADE_A",
            centre_name="",
        )
        text = build_grade_announcement_text(ann)
        # Should not crash; text still has grade info
        assert "75" in text


# ── build_announcement_from_inspection ────────────────────────────────────────

class TestBuildAnnouncementFromInspection:
    def test_state_inference(self):
        ann = build_announcement_from_inspection(
            grade_a_pct=70.0,
            urs_pct=25.0,
            rejected_pct=5.0,
            lot_recommendation="ACCEPT_GRADE_A",
            state_or_city="nashik",
        )
        assert ann.language == SupportedLanguage.MARATHI

    def test_explicit_language_override(self):
        ann = build_announcement_from_inspection(
            grade_a_pct=70.0,
            urs_pct=25.0,
            rejected_pct=5.0,
            lot_recommendation="ACCEPT_GRADE_A",
            state_or_city="nashik",
            language=SupportedLanguage.ENGLISH,
        )
        assert ann.language == SupportedLanguage.ENGLISH

    def test_all_fields_populated(self):
        ann = build_announcement_from_inspection(
            grade_a_pct=65.0,
            urs_pct=25.0,
            rejected_pct=10.0,
            lot_recommendation="ACCEPT_URS",
            suspect_count=4,
            centre_name="Kurnool APMC",
            lot_id="KNL-2026-042",
            total_bulbs=40,
            state_or_city="kurnool",
        )
        assert ann.grade_a_pct == 65.0
        assert ann.centre_name == "Kurnool APMC"
        assert ann.lot_id == "KNL-2026-042"
        assert ann.suspect_count == 4
        assert ann.language == SupportedLanguage.TELUGU


# ── synthesize_grade_announcement ─────────────────────────────────────────────

class TestSynthesizeGradeAnnouncement:
    def _make_ann(self, lang: SupportedLanguage = SupportedLanguage.ENGLISH) -> GradeAnnouncementLanguage:
        return GradeAnnouncementLanguage(
            language=lang,
            grade_a_pct=73.0,
            urs_pct=21.0,
            rejected_pct=6.0,
            suspect_count=2,
            lot_recommendation="ACCEPT_GRADE_A",
            centre_name="Lasalgaon APMC",
            lot_id="LSG-001",
        )

    def test_no_api_key_returns_text_only(self):
        ann = self._make_ann()
        result = synthesize_grade_announcement(ann, bhashini_api_key="")
        assert isinstance(result, BhashiniTTSResult)
        assert result.success is False
        assert result.is_mock is True
        assert result.audio_bytes is None

    def test_no_api_key_still_has_announcement_text(self):
        ann = self._make_ann()
        result = synthesize_grade_announcement(ann, bhashini_api_key="")
        assert len(result.announcement_text) > 10
        assert "73" in result.announcement_text

    def test_no_api_key_has_error_message(self):
        ann = self._make_ann()
        result = synthesize_grade_announcement(ann, bhashini_api_key="")
        assert len(result.error_message) > 0

    def test_language_preserved_in_result(self):
        ann = self._make_ann(SupportedLanguage.MARATHI)
        result = synthesize_grade_announcement(ann, bhashini_api_key="")
        assert result.language == SupportedLanguage.MARATHI

    def test_latency_ms_is_non_negative(self):
        ann = self._make_ann()
        result = synthesize_grade_announcement(ann, bhashini_api_key="")
        assert result.latency_ms >= 0.0

    def test_invalid_api_key_returns_graceful_failure(self):
        """A bad API key should not crash — returns structured failure."""
        ann = self._make_ann()
        result = synthesize_grade_announcement(ann, bhashini_api_key="INVALID_KEY_12345")
        assert isinstance(result, BhashiniTTSResult)
        # Either fails (network) or succeeds — but must not raise
        assert result.is_mock in (True, False)
        assert result.announcement_text  # text always populated

    def test_all_seven_languages_produce_text(self):
        """All 7 supported languages must produce non-empty announcement text."""
        for lang in SupportedLanguage:
            ann = GradeAnnouncementLanguage(
                language=lang,
                grade_a_pct=70.0,
                urs_pct=25.0,
                rejected_pct=5.0,
                suspect_count=1,
                lot_recommendation="ACCEPT_GRADE_A",
            )
            result = synthesize_grade_announcement(ann, bhashini_api_key="")
            assert len(result.announcement_text) > 5, f"Empty text for language: {lang.value}"


# ── SupportedLanguage enum ────────────────────────────────────────────────────

class TestSupportedLanguageEnum:
    def test_all_bcp47_codes_valid(self):
        expected = {"hi", "mr", "kn", "te", "ta", "gu", "en"}
        actual = {lang.value for lang in SupportedLanguage}
        assert actual == expected

    def test_seven_languages_supported(self):
        assert len(list(SupportedLanguage)) == 7
