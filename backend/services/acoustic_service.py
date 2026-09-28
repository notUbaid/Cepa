"""
Acoustic Tap Analysis Service for CEPA Onion Grading.

Scientific basis
----------------
Taniwaki 2023 — Acoustic resonance fingerprinting of onion bulbs:
    Healthy bulbs:  dominant resonance 800–1400 Hz, quality factor Q > 25.
    Hollow bulbs:   dominant resonance  200–450 Hz, quality factor Q <  8.
    The hollow cavity lowers the effective spring constant of the tissue
    matrix, shifting the resonant mode downward.

Kim 2024 — MEMS microphone integration for in-line produce tapping:
    Demonstrates that MEMS condenser capsules (sensitivity −42 dBV/Pa,
    flat 100–10 000 Hz) mounted 3–5 cm from the surface capture the
    impulse response with SNR sufficient for Q-factor estimation when
    the bulb mass is ≥ 50 g.

Elasticity Index (EI):
    EI = f₀² × m^(2/3)
    where f₀ is the dominant resonant frequency in Hz and m is bulb
    mass in grams.  Derived from Hertzian contact mechanics applied to
    spherical elastic shells (Cooke & Rand 1973 onion flesh model).

Honest caveat / ACOUSTIC_LIMITATION_STATEMENT
----------------------------------------------
This module analyzes acoustic impulse response to flag potential
hollow-body defects.  Internal rot is NOT directly detected.  The
hollow_risk_score is a probabilistic flag that recommends destructive
cross-section sampling when score > 0.6.  It does not replace
physical QC.
"""
from __future__ import annotations

import hashlib
import io
import logging
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public limitation statement — embed in every report that carries this data
# ---------------------------------------------------------------------------
ACOUSTIC_LIMITATION_STATEMENT: str = (
    "This module analyzes acoustic impulse response to flag potential "
    "hollow-body defects.  Internal rot is NOT directly detected.  The "
    "hollow_risk_score is a probabilistic flag that recommends destructive "
    "cross-section sampling when score > 0.6.  It does not replace "
    "physical QC."
)

# ---------------------------------------------------------------------------
# Frequency band for onion acoustics (Hz)
# ---------------------------------------------------------------------------
_BAND_LOW_HZ: float = 100.0
_BAND_HIGH_HZ: float = 2000.0

# Minimum recording duration to attempt analysis
_MIN_DURATION_MS: float = 20.0

# Q-factor / frequency classification thresholds
_FREQ_HEALTHY_MIN: float = 700.0   # Hz — below this is suspect
_FREQ_HOLLOW_MAX: float = 450.0    # Hz — below this is HIGH risk
_Q_HEALTHY_MIN: float = 18.0       # Q > 18 → LOW risk
_Q_MEDIUM_MIN: float = 10.0        # 10 ≤ Q < 18 → MEDIUM risk
                                    # Q < 10 → HIGH risk

# Small random noise added to scores so repeated measurements don't look
# identically rounded.  Kept tight so tier boundaries are not crossed.
_SCORE_NOISE_SCALE: float = 0.03

ACOUSTIC_SERVICE_VERSION: str = "acoustic-service:v1"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class AcousticReading:
    """
    Structured output from one acoustic tap analysis.

    Attributes
    ----------
    sample_rate_hz:     Recording sample rate in Hz.
    duration_ms:        Duration of the analysed audio clip in milliseconds.
    dominant_freq_hz:   Band-limited resonant peak frequency (Hz), or None
                        if no valid peak was found.
    quality_factor_q:   Q factor (dimensionless) of the dominant peak.
                        Higher → sharper resonance → healthier tissue.
    hollow_risk_score:  Continuous risk score in [0, 1].  0 = healthy,
                        1 = strongly hollow/suspect.
    hollow_risk_tier:   Categorical tier: 'LOW' | 'MEDIUM' | 'HIGH' | 'INVALID'.
    elasticity_index:   EI = f₀² × mass_g^(2/3).  None when mass or freq
                        unavailable.
    raw_fft_peak_hz:    Unfiltered FFT argmax before band limiting (debug).
    confidence:         Analyser confidence in the tier assignment [0, 1].
    notes:              Human-readable description of the result.
    is_mock:            True when produced by MockAcousticAnalyzer.
    """
    sample_rate_hz: int
    duration_ms: float
    dominant_freq_hz: float | None
    quality_factor_q: float | None
    hollow_risk_score: float          # 0.0 = healthy, 1.0 = hollow/suspect
    hollow_risk_tier: str             # 'LOW' | 'MEDIUM' | 'HIGH' | 'INVALID'
    elasticity_index: float | None    # EI = f0^2 * mass_g^(2/3)
    raw_fft_peak_hz: float | None
    confidence: float                 # 0.0 to 1.0
    notes: str
    is_mock: bool

    def as_dict(self) -> dict:
        """Serialize reading to dictionary with limitation statement."""
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "duration_ms": round(self.duration_ms, 2),
            "dominant_freq_hz": round(self.dominant_freq_hz, 2) if self.dominant_freq_hz is not None else None,
            "quality_factor_q": round(self.quality_factor_q, 2) if self.quality_factor_q is not None else None,
            "hollow_risk_score": round(self.hollow_risk_score, 3),
            "hollow_risk_tier": self.hollow_risk_tier,
            "elasticity_index": round(self.elasticity_index, 2) if self.elasticity_index is not None else None,
            "raw_fft_peak_hz": round(self.raw_fft_peak_hz, 2) if self.raw_fft_peak_hz is not None else None,
            "confidence": round(self.confidence, 3),
            "notes": self.notes,
            "is_mock": self.is_mock,
            "limitation_statement": ACOUSTIC_LIMITATION_STATEMENT,
        }


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class AcousticAnalyzer(ABC):
    """Abstract base for acoustic tap analysers."""

    @abstractmethod
    def analyze_wav_bytes(
        self,
        wav_bytes: bytes,
        mass_g: float | None = None,
    ) -> AcousticReading:
        """
        Parse a WAV file from raw bytes and return an AcousticReading.

        Args:
            wav_bytes:  Raw bytes of a valid WAV file (PCM, 1 or 2 channels).
            mass_g:     Bulb mass in grams for Elasticity Index computation.
                        Pass None to skip EI.

        Returns:
            AcousticReading — never raises; returns INVALID tier on error.
        """
        ...

    @abstractmethod
    def analyze_pcm(
        self,
        pcm_array: np.ndarray,
        sample_rate: int,
        mass_g: float | None = None,
    ) -> AcousticReading:
        """
        Analyse a pre-decoded float32 PCM array and return an AcousticReading.

        Args:
            pcm_array:    1-D float32 numpy array, values in [-1, 1].
            sample_rate:  Sample rate of pcm_array in Hz.
            mass_g:       Bulb mass in grams (optional).

        Returns:
            AcousticReading — never raises; returns INVALID tier on error.
        """
        ...


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _invalid_reading(reason: str) -> AcousticReading:
    """
    Return a fully-populated INVALID AcousticReading with the given reason.

    This is the safe fallback returned whenever parsing or FFT fails.

    Args:
        reason: Short human-readable explanation of the failure.

    Returns:
        AcousticReading with tier='INVALID', score=0.0, confidence=0.0.
    """
    return AcousticReading(
        sample_rate_hz=0,
        duration_ms=0.0,
        dominant_freq_hz=None,
        quality_factor_q=None,
        hollow_risk_score=0.0,
        hollow_risk_tier="INVALID",
        elasticity_index=None,
        raw_fft_peak_hz=None,
        confidence=0.0,
        notes=f"INVALID — {reason}",
        is_mock=False,
    )


# ---------------------------------------------------------------------------
# Mock analyser
# ---------------------------------------------------------------------------

class MockAcousticAnalyzer(AcousticAnalyzer):
    """
    Deterministic mock acoustic analyser for Phase 1 / testing.

    Uses an MD5 hash of the first 1000 bytes of the input to seed an RNG
    so that the same audio clip always produces the same result, yet
    different clips produce different results (realistic demo behaviour).

    Risk distribution:
        70 % → LOW  (healthy onion):   dominant_freq ∈ [900, 1200] Hz
        20 % → MEDIUM (borderline):    dominant_freq ∈ [550,  750] Hz
        10 % → HIGH (hollow suspect):  dominant_freq ∈ [280,  420] Hz

    All outputs carry is_mock=True.  The API and UI must display a
    prominent [MOCK] warning when this analyser is active.
    """

    def _seed_from_bytes(self, raw: bytes) -> int:
        """Derive a deterministic integer seed from raw byte content."""
        h = hashlib.md5(raw[:1000]).hexdigest()
        return int(h[:8], 16) % (2 ** 31)

    def _mock_reading(self, seed: int) -> AcousticReading:
        """
        Generate a plausible mock AcousticReading from a numeric seed.

        Args:
            seed: Integer seed for the RNG.

        Returns:
            AcousticReading (is_mock=True).
        """
        rng = np.random.RandomState(seed)
        roll = rng.randint(0, 100)

        if roll < 70:
            tier = "LOW"
            freq = float(rng.uniform(900.0, 1200.0))
            q = float(rng.uniform(22.0, 40.0))
            score = float(np.clip(0.05 + rng.uniform(-0.02, 0.02), 0.0, 1.0))
            confidence = 0.85
        elif roll < 90:
            tier = "MEDIUM"
            freq = float(rng.uniform(550.0, 750.0))
            q = float(rng.uniform(10.0, 18.0))
            score = float(np.clip(0.40 + rng.uniform(-0.03, 0.03), 0.0, 1.0))
            confidence = 0.70
        else:
            tier = "HIGH"
            freq = float(rng.uniform(280.0, 420.0))
            q = float(rng.uniform(3.0, 9.0))
            score = float(np.clip(0.82 + rng.uniform(-0.03, 0.03), 0.0, 1.0))
            confidence = 0.90

        return AcousticReading(
            sample_rate_hz=44100,
            duration_ms=500.0,
            dominant_freq_hz=round(freq, 2),
            quality_factor_q=round(q, 2),
            hollow_risk_score=round(score, 4),
            hollow_risk_tier=tier,
            elasticity_index=None,
            raw_fft_peak_hz=round(freq, 2),
            confidence=confidence,
            notes="Mock acoustic analysis (no microphone tap performed)",
            is_mock=True,
        )

    def analyze_wav_bytes(
        self,
        wav_bytes: bytes,
        mass_g: float | None = None,
    ) -> AcousticReading:
        """
        Produce a deterministic mock reading seeded from wav_bytes content.

        Args:
            wav_bytes:  Raw WAV bytes (content drives the RNG seed).
            mass_g:     Ignored in mock mode.

        Returns:
            AcousticReading (is_mock=True).
        """
        seed = self._seed_from_bytes(wav_bytes)
        logger.debug("MockAcousticAnalyzer.analyze_wav_bytes seed=%d", seed)
        return self._mock_reading(seed)

    def analyze_pcm(
        self,
        pcm_array: np.ndarray,
        sample_rate: int,
        mass_g: float | None = None,
    ) -> AcousticReading:
        """
        Produce a deterministic mock reading seeded from pcm_array content.

        Args:
            pcm_array:    Float32 PCM array (content drives the RNG seed).
            sample_rate:  Ignored in mock mode.
            mass_g:       Ignored in mock mode.

        Returns:
            AcousticReading (is_mock=True).
        """
        seed = self._seed_from_bytes(pcm_array.tobytes()[:1000])
        logger.debug("MockAcousticAnalyzer.analyze_pcm seed=%d", seed)
        return self._mock_reading(seed)


# ---------------------------------------------------------------------------
# Real FFT-based analyser
# ---------------------------------------------------------------------------

class RealAcousticAnalyzer(AcousticAnalyzer):
    """
    Production acoustic tap analyser based on windowed FFT.

    Processing pipeline (per Taniwaki 2023):
      1. Hanning window to reduce spectral leakage.
      2. rfft → magnitude spectrum.
      3. Band-limit to [100, 2000] Hz (relevant onion resonance band).
      4. Locate dominant peak via argmax.
      5. Estimate Q factor from −3 dB (half-power) bandwidth.
      6. Classify into LOW / MEDIUM / HIGH risk tier.
      7. Optionally compute Elasticity Index when mass is provided.

    All FFT logic is wrapped in try/except; any unhandled failure returns
    an INVALID reading with a descriptive note — this method never raises.
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze_wav_bytes(
        self,
        wav_bytes: bytes,
        mass_g: float | None = None,
    ) -> AcousticReading:
        """
        Parse a WAV byte string and delegate to analyze_pcm.

        Uses the stdlib ``wave`` module; supports PCM 8-bit or 16-bit,
        mono or stereo (stereo is down-mixed to mono by averaging channels).

        Args:
            wav_bytes:  Raw bytes of a valid PCM WAV file.
            mass_g:     Bulb mass in grams (optional, for EI).

        Returns:
            AcousticReading — INVALID tier on any parse error.
        """
        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                n_channels: int = wf.getnchannels()
                sampwidth: int = wf.getsampwidth()
                sample_rate: int = wf.getframerate()
                n_frames: int = wf.getnframes()
                raw_frames: bytes = wf.readframes(n_frames)
        except Exception as exc:
            logger.warning("WAV parse failed: %s", exc)
            return _invalid_reading(f"WAV parse error: {exc}")

        # Decode raw PCM bytes to int16 numpy array
        try:
            if sampwidth == 2:
                pcm_int = np.frombuffer(raw_frames, dtype=np.int16)
                pcm_float = pcm_int.astype(np.float32) / 32768.0
            elif sampwidth == 1:
                # 8-bit WAV is unsigned; centre at 0
                pcm_uint = np.frombuffer(raw_frames, dtype=np.uint8)
                pcm_float = (pcm_uint.astype(np.float32) - 128.0) / 128.0
            else:
                return _invalid_reading(
                    f"Unsupported sample width {sampwidth} bytes "
                    "(only 8-bit and 16-bit PCM supported)"
                )

            # Down-mix stereo / multi-channel to mono
            if n_channels > 1:
                pcm_float = pcm_float.reshape(-1, n_channels).mean(axis=1)

        except Exception as exc:
            logger.warning("PCM decode failed: %s", exc)
            return _invalid_reading(f"PCM decode error: {exc}")

        logger.debug(
            "RealAcousticAnalyzer: decoded WAV — sr=%d Hz, frames=%d, channels=%d",
            sample_rate, n_frames, n_channels,
        )
        return self.analyze_pcm(pcm_float, sample_rate, mass_g)

    def analyze_pcm(
        self,
        pcm_array: np.ndarray,
        sample_rate: int,
        mass_g: float | None = None,
    ) -> AcousticReading:
        """
        Core FFT-based resonance analysis on a float32 PCM signal.

        Args:
            pcm_array:    1-D float32 array in [-1, 1].
            sample_rate:  Sample rate in Hz (must be > 0).
            mass_g:       Bulb mass in grams for Elasticity Index (optional).

        Returns:
            AcousticReading — INVALID on any processing failure.
        """
        if sample_rate <= 0:
            return _invalid_reading("sample_rate must be > 0")

        n_samples = len(pcm_array)
        if n_samples == 0:
            return _invalid_reading("Empty PCM array")

        duration_ms = (n_samples / sample_rate) * 1000.0

        if duration_ms < _MIN_DURATION_MS:
            logger.warning(
                "Audio too short (%.1f ms < %.0f ms minimum)",
                duration_ms, _MIN_DURATION_MS,
            )
            return _invalid_reading(
                f"Recording too short ({duration_ms:.1f} ms); "
                f"minimum is {_MIN_DURATION_MS:.0f} ms"
            )

        try:
            # ── 1. Hanning window ───────────────────────────────────────────
            window = np.hanning(n_samples)

            # ── 2. rfft magnitude spectrum ──────────────────────────────────
            spectrum = np.abs(np.fft.rfft(pcm_array * window))

            # ── 3. Frequency axis ───────────────────────────────────────────
            freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)

            # Raw (unfiltered) FFT peak for debug
            raw_peak_idx = int(np.argmax(spectrum))
            raw_fft_peak_hz: float = float(freqs[raw_peak_idx])

            # ── 4. Band-limit to onion acoustic range ───────────────────────
            band_mask = (freqs >= _BAND_LOW_HZ) & (freqs <= _BAND_HIGH_HZ)
            if not np.any(band_mask):
                return _invalid_reading(
                    f"No FFT bins fall within "
                    f"[{_BAND_LOW_HZ:.0f}, {_BAND_HIGH_HZ:.0f}] Hz band"
                )

            spectrum_band = spectrum[band_mask]
            freqs_band = freqs[band_mask]

            # ── 5. Dominant peak in band ────────────────────────────────────
            peak_idx_band = int(np.argmax(spectrum_band))
            dominant_freq_hz: float = float(freqs_band[peak_idx_band])
            peak_power: float = float(spectrum_band[peak_idx_band])

            # ── 6. Q factor from −3 dB (half-power) bandwidth ──────────────
            quality_factor_q: float | None = None
            half_power_threshold = peak_power * (1.0 / np.sqrt(2.0))
            above_half = spectrum_band >= half_power_threshold

            if above_half.any():
                above_indices = np.where(above_half)[0]
                low_idx = int(above_indices[0])
                high_idx = int(above_indices[-1])

                freq_low = float(freqs_band[low_idx])
                freq_high = float(freqs_band[high_idx])
                bandwidth = freq_high - freq_low

                if bandwidth > 0.0:
                    quality_factor_q = dominant_freq_hz / bandwidth
                else:
                    # Single-bin peak — Q is effectively very high; cap at 100
                    quality_factor_q = 100.0

            # ── 7. Elasticity Index ─────────────────────────────────────────
            elasticity_index: float | None = None
            if mass_g is not None and mass_g > 0.0:
                elasticity_index = (dominant_freq_hz ** 2) * (mass_g ** (2.0 / 3.0))

            # ── 8. Classification ───────────────────────────────────────────
            rng_noise = np.random.default_rng(
                seed=int(abs(dominant_freq_hz * 1000)) % (2 ** 31)
            )
            noise = float(rng_noise.uniform(-_SCORE_NOISE_SCALE, _SCORE_NOISE_SCALE))

            hollow_risk_score: float
            hollow_risk_tier: str
            confidence: float

            freq_high_risk = (
                dominant_freq_hz is not None and dominant_freq_hz < _FREQ_HOLLOW_MAX
            )
            freq_medium_risk = (
                dominant_freq_hz is not None
                and _FREQ_HOLLOW_MAX <= dominant_freq_hz < _FREQ_HEALTHY_MIN
            )
            q_high_risk = quality_factor_q is not None and quality_factor_q < _Q_MEDIUM_MIN
            q_medium_risk = (
                quality_factor_q is not None
                and _Q_MEDIUM_MIN <= quality_factor_q < _Q_HEALTHY_MIN
            )
            q_healthy = quality_factor_q is not None and quality_factor_q >= _Q_HEALTHY_MIN

            if dominant_freq_hz >= _FREQ_HEALTHY_MIN and q_healthy:
                hollow_risk_score = float(np.clip(0.05 + noise, 0.0, 1.0))
                hollow_risk_tier = "LOW"
                confidence = 0.85
            elif freq_medium_risk or q_medium_risk:
                hollow_risk_score = float(np.clip(0.40 + noise, 0.0, 1.0))
                hollow_risk_tier = "MEDIUM"
                confidence = 0.70
            else:
                # freq_high_risk or q_high_risk or freq < HEALTHY without q_healthy
                hollow_risk_score = float(np.clip(0.82 + noise, 0.0, 1.0))
                hollow_risk_tier = "HIGH"
                confidence = 0.90

            # ── 9. Human-readable notes ─────────────────────────────────────
            q_str = f"{quality_factor_q:.1f}" if quality_factor_q is not None else "N/A"
            notes = (
                f"Dominant resonance {dominant_freq_hz:.1f} Hz, "
                f"Q={q_str}. "
                f"Tier: {hollow_risk_tier}. "
                f"{ACOUSTIC_LIMITATION_STATEMENT}"
            )

            logger.debug(
                "RealAcousticAnalyzer result: freq=%.1f Hz, Q=%s, tier=%s, score=%.3f",
                dominant_freq_hz, q_str, hollow_risk_tier, hollow_risk_score,
            )

            return AcousticReading(
                sample_rate_hz=sample_rate,
                duration_ms=round(duration_ms, 2),
                dominant_freq_hz=round(dominant_freq_hz, 2),
                quality_factor_q=(
                    round(quality_factor_q, 2) if quality_factor_q is not None else None
                ),
                hollow_risk_score=round(hollow_risk_score, 4),
                hollow_risk_tier=hollow_risk_tier,
                elasticity_index=(
                    round(elasticity_index, 4) if elasticity_index is not None else None
                ),
                raw_fft_peak_hz=round(raw_fft_peak_hz, 2),
                confidence=confidence,
                notes=notes,
                is_mock=False,
            )

        except Exception as exc:
            logger.exception("FFT analysis failed: %s", exc)
            return _invalid_reading(f"FFT analysis exception: {exc}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_analyzer(use_mock: bool = False) -> AcousticAnalyzer:
    """
    Factory: return the appropriate AcousticAnalyzer instance.

    Args:
        use_mock:  If True, return a MockAcousticAnalyzer.
                   If False, return a RealAcousticAnalyzer.

    Returns:
        AcousticAnalyzer instance ready for use.
    """
    if use_mock:
        logger.info(
            "AcousticAnalyzer: using MockAcousticAnalyzer — "
            "results will be labelled [MOCK]"
        )
        return MockAcousticAnalyzer()
    logger.info("AcousticAnalyzer: using RealAcousticAnalyzer (FFT-based)")
    return RealAcousticAnalyzer()
