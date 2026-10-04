# System Limitations & Engineering Constraints

A core tenet of the Cepa project is absolute scientific honesty: **the project must feel like an inspection instrument, not an AI toy**. This document clearly delineates what the system can and cannot do.

---

## 1. Internal Rot is Inaccessible to Optical Cameras
- **Physical Reality**: RGB phone sensors capture light reflected exclusively from the outer tunic (dry skin) and exposed surface tissues of the bulb.
- **The Constraint**: Internal bacterial soft rot (*Dickeya/Pectobacterium*), black mold hidden beneath outer papery scales (*Aspergillus niger*), or fusarium basal rot that has not reached the outer surface cannot be detected from surface photographs alone.
- **System Policy**: Cepa never claims to detect internal defects. The mobile UI and every generated PDF report carry an explicit disclaimer:
  > *"Visual surface examination only. Internal rot and defects not visible from the exterior cannot be detected."*

---

## 2. Projected 2D Geometry vs. Caliper Sizing
- **Physical Reality**: An onion bulb is a triaxial spheroid resting on a flat plane.
- **The Constraint**: A top-down 2D photograph captures an orthographic projection of the bulb's upper hemisphere.
  - Sizing derived from mask area ($D_{\text{eq}} = 2\sqrt{\frac{A}{\pi}}$) represents the diameter of an equivalent circular disk.
  - Sizing using fitted ellipses ($D_{\text{major}}, D_{\text{minor}}$) captures visible planar axes.
  - If a bulb is oriented vertically (neck pointing up) vs horizontally (neck sideways), the projected equatorial width varies by approximately $\pm 5\text{ mm} - 12\text{ mm}$.
- **System Policy**: The system marks all size values with `projection_note` and activates `uncertainty_flag = True` whenever a bulb's diameter falls within $3\text{ mm}$ of any grading threshold.

---

## 3. Sampling Coverage & Heap Representativeness
- **Physical Reality**: A commercial onion lot typically arrives in tractor trolleys or 50 kg jute sacks comprising $500 - 5,000\text{ kg}$ ($5,000 - 50,000\text{ bulbs}$).
- **The Constraint**: A single photograph captures $10 - 25\text{ bulbs}$ arranged on an inspection mat ($< 0.5\%$ of the total lot).
- **System Policy**:
  - The database architecture is multi-sample (`Sample` entities nested under `Inspection`).
  - The aggregator computes coverage and includes a mandatory sampling notice:
    > *"Lot result based on N sample(s). Single-sample inspection may not represent the full lot."*
  - The app encourages procurement officers to take multiple random samples from top, middle, and bottom tiers of the consignment.

---

## 4. Optical Distortions & Scale Limits
- **Planar Coplanarity Assumption**: Homography calibration assumes that the onion's equator lies in the exact same plane as the ChArUco board ($Z=0$). While planar RMS calibration error is sub-millimeter ($\le 0.4\text{ mm}$), an onion bulb elevates its equatorial cross-section $20 - 40\text{ mm}$ above the board, introducing an empirical 3D parallax uncertainty of $\pm 1.5 - 3.5\text{ mm}$.
- **Scale Boundaries**: Any calibration producing $\text{scale} < 0.05\text{ mm/px}$ or $> 5.0\text{ mm/px}$ is marked invalid (`scale_unreliable`), preventing wildly erroneous measurements. Uncalibrated fallback defaults to $\pm 5.0\text{ mm}$ and forces `NEEDS_REVIEW`.

---

## 5. Acoustic Resonance Tap Spectroscopy Scope
- **Physical Reality**: Mobile smartphone microphones in noisy APMC mandi environments lack direct physical acoustic contact with the bulb tunic and suffer high ambient acoustic noise ($> 75\text{ dB}$ mandi decibels).
- **The Constraint**: Smartphone audio recordings cannot reliably isolate the resonant ring frequency ($f_0 \approx 750\text{ Hz}$) of individual hand-tapped bulbs in real field settings.
- **System Policy**: Acoustic resonant frequency analysis is implemented strictly as an experimental backend research API endpoint (`POST /api/v1/inspections/{id}/acoustic`) designed for laboratory fixtures equipped with contact piezoelectric transducers. Mobile client builds do not claim automated in-app acoustic tap grading.
