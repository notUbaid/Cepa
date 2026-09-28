"""
Tests for Acoustic Tap Analysis Service (Internal Hollow-Body & Cavity Decay Detection)
Citing [Taniwaki-2023], [Kim-2024], [AGMARK-2004]
"""
import io
import math
import struct
import wave
import pytest
import numpy as np

from services.acoustic_service import (
    AcousticAnalyzer,
    AcousticReading,
    RealAcousticAnalyzer,
    MockAcousticAnalyzer,
    get_analyzer,
    ACOUSTIC_LIMITATION_STATEMENT,
)


def _generate_synthetic_wav(freq_hz: float, duration_ms: float = 100.0, sample_rate: int = 44100, amplitude: float = 0.8) -> bytes:
    """Generate in-memory synthetic PCM WAV bytes."""
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = bytearray()
        for i in range(n_samples):
            val = int(32767 * amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate))
            # clamp to int16
            val = max(-32768, min(32767, val))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    return wav_io.getvalue()


class TestAcousticAnalyzerFactory:
    def test_get_mock_analyzer(self):
        analyzer = get_analyzer(use_mock=True)
        assert isinstance(analyzer, MockAcousticAnalyzer)

    def test_get_real_analyzer(self):
        analyzer = get_analyzer(use_mock=False)
        assert isinstance(analyzer, RealAcousticAnalyzer)


class TestMockAcousticAnalyzer:
    def test_deterministic_behavior(self):
        analyzer = MockAcousticAnalyzer()
        wav = _generate_synthetic_wav(1000.0)
        r1 = analyzer.analyze_wav_bytes(wav, mass_g=120.0)
        r2 = analyzer.analyze_wav_bytes(wav, mass_g=120.0)
        assert r1.dominant_freq_hz == r2.dominant_freq_hz
        assert r1.hollow_risk_tier == r2.hollow_risk_tier
        assert r1.is_mock is True

    def test_as_dict(self):
        analyzer = MockAcousticAnalyzer()
        wav = _generate_synthetic_wav(1000.0)
        r = analyzer.analyze_wav_bytes(wav)
        d = r.as_dict()
        assert "dominant_freq_hz" in d
        assert "hollow_risk_tier" in d
        assert "hollow_risk_score" in d


class TestRealAcousticAnalyzer:
    def test_healthy_resonance_high_frequency(self):
        """Healthy sound bulb has dominant resonance 800-1400 Hz -> LOW risk tier."""
        analyzer = RealAcousticAnalyzer()
        wav = _generate_synthetic_wav(1050.0, duration_ms=100.0)
        reading = analyzer.analyze_wav_bytes(wav, mass_g=110.0)
        assert reading.is_mock is False
        assert reading.dominant_freq_hz is not None
        assert 950 <= reading.dominant_freq_hz <= 1150
        assert reading.hollow_risk_tier == "LOW"
        assert reading.hollow_risk_score < 0.35
        assert reading.elasticity_index is not None

    def test_hollow_body_low_frequency(self):
        """Hollow cavity defect has low dominant resonance < 450 Hz -> HIGH risk tier."""
        analyzer = RealAcousticAnalyzer()
        wav = _generate_synthetic_wav(320.0, duration_ms=100.0)
        reading = analyzer.analyze_wav_bytes(wav, mass_g=110.0)
        assert reading.is_mock is False
        assert reading.dominant_freq_hz is not None
        assert 250 <= reading.dominant_freq_hz <= 400
        assert reading.hollow_risk_tier == "HIGH"
        assert reading.hollow_risk_score > 0.60

    def test_too_short_duration_invalid(self):
        """Recording < 20 ms returns INVALID reading."""
        analyzer = RealAcousticAnalyzer()
        wav = _generate_synthetic_wav(1000.0, duration_ms=10.0)
        reading = analyzer.analyze_wav_bytes(wav)
        assert reading.hollow_risk_tier == "INVALID"
        assert reading.confidence == 0.0

    def test_corrupt_bytes_graceful_handling(self):
        analyzer = RealAcousticAnalyzer()
        reading = analyzer.analyze_wav_bytes(b"NOT A WAV FILE")
        assert reading.hollow_risk_tier == "INVALID"
        assert reading.dominant_freq_hz is None

    def test_limitation_statement_presence(self):
        assert "probabilistic" in ACOUSTIC_LIMITATION_STATEMENT.lower() or "limitation" in ACOUSTIC_LIMITATION_STATEMENT.lower() or "Taniwaki" in ACOUSTIC_LIMITATION_STATEMENT
