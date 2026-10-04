# CEPA Mandi Assaying Workstation — Hardware Specification & Assembly Guide

This document defines the physical hardware architecture, optical setup, and sensor integration specifications for the **CEPA (Certified and Evidenced Produce Assessment)** field inspection station deployed at APMC mandi intake gates, cold storages, and NAFED buffer procurement centers.

---

## 1. Physical Gantry & Enclosure Architecture

Field conditions at agricultural marketing yards in Lasalgaon and Pimpalgaon present extreme airborne dust, fluctuating ambient solar illuminance (5,000 to 100,000 lux), and mechanical vibrations from tractor-trolley movement. The assaying workstation employs a modular, rigid, anti-vibration aluminum extrusion frame:

```
                      +-----------------------------+
                      |   Sony IMX219 / 1080p Lens  |
                      |   Overhead Nadir Camera      |
                      +--------------+--------------+
                                     |
                                     |  H_0 = 420 mm +/- 10 mm
                                     |
                      +--------------v--------------+
                      |   CRI > 95 Ring Diffuser    |
                      |   5000K Neutral Polarization|
                      +--------------+--------------+
                                     |
    +--------------------------------+--------------------------------+
    |                                                                 |
    |    [Bulb 1]          [Bulb 2]          [Bulb 3]                 |
    |                                                                 |
    |                                    +-----------------------+    |
    |    [Bulb 4]          [Bulb 5]      | ChArUco 7x5 Board     |    |
    |                                    | 20mm sq / 15mm ArUco  |    |
    |                                    +-----------------------+    |
    +-----------------------------------------------------------------+
    |        Matt Non-Reflective Anodized Staging Base (400x400 mm)   |
    +-----------------------------------------------------------------+
```

### Mechanical Bill of Materials (BOM)

| Component | Specification | Quantity | Primary Purpose |
|:---|:---|:---:|:---|
| **Structural Frame** | 2020 Aluminum V-Slot Extrusion (Black Anodized) | 4 × 500mm, 8 × 400mm | Rigid support frame with 90° corner brackets |
| **Stage Surface** | 6mm Matte Black Cast Acrylic / Anodized Aluminum | 1 × 450×450 mm | Non-reflective background ($L^* < 15$) for high-contrast segmentation |
| **Camera Mount** | 3D-Printed / CNC Aluminum Gantry with Micrometer Screw | 1 unit | Vertical nadir alignment ($H_0 = 420\text{ mm}$) with $\pm 5^\circ$ pitch adjustment |
| **Anti-Vibration Feet**| Nitrile Rubber M8 Leveling Isolation Dampeners | 4 units | Isolates optical sensors from vehicular rumble and heavy handling |

---

## 2. Optical Acquisition Subsystem

### 2.1 Camera Sensor Specifications
- **Sensor:** Sony IMX219 (8.08 MP) or UVC-Compliant 1080p Industrial CMOS sensor
- **Active Array:** $3280 \times 2464$ pixels (downsampled to $1920 \times 1080$ for low-latency streaming at 30 FPS)
- **Pixel Size:** $1.12\,\mu\text{m} \times 1.12\,\mu\text{m}$
- **Lens Focal Length ($f$):** $3.04\text{ mm}$ fixed focal length
- **Field of View (FOV):** $62.2^\circ$ Horizontal, $48.8^\circ$ Vertical
- **Working Distance ($H_0$):** $420\text{ mm}$ (nominal nadir height above staging plane)
- **Field of Coverage:** Approximately $480\text{ mm} \times 270\text{ mm}$, accommodating 15–20 bulbs per batch

### 2.2 Controlled Diffuse Illumination
- **Light Source:** High-CRI LED Ring Light array (96 SMD LEDs)
- **Color Rendering Index (CRI):** $R_a \ge 95$, $R_9 \ge 90$ (critical for accurate CIELAB anthocyanin pigment detection)
- **Color Temperature ($T_c$):** $5000\text{ K} \pm 200\text{ K}$ (neutral daylight standard)
- **Illuminance at Sample Plane:** $1,500 - 2,000\text{ lux}$ (uniformity $> 92\%$ across active inspection field)
- **Diffuser:** Frosted optical polycarbonate diffusion dome with linear polarizing filter cross-polarized against lens filter to suppress specular glint on waxy allium tunic skins.

---

## 3. Metric Calibration Target (ChArUco 7×5)

### 3.1 Geometric Parameters
To eliminate perspective tilt and lens radial distortion without requiring manual caliper measurements, the workstation utilizes a permanently mounted ChArUco target:

- **Board Configuration:** 7 columns × 5 rows (35 total checker squares)
- **Square Length ($S$):** $20.0\text{ mm} \pm 0.05\text{ mm}$
- **Marker Length ($M$):** $15.0\text{ mm} \pm 0.05\text{ mm}$
- **Dictionary:** `cv2.aruco.DICT_5X5_100` (100 unique 5×5 bit identifiers)
- **Sub-Pixel Corner Refinement:** Corner sub-pixel interpolation with a $5 \times 5$ window and stop criteria $(\text{EPS} + \text{COUNT}, 30, 0.01)$.

### 3.2 Target Generation & Fabrication
The board can be generated directly via the CEPA CLI:
```bash
python -m backend.cli generate-board --output charuco_board_7x5.png
```
Fabrication Guidelines:
1. Print on non-reflective synthetic polyester card stock (minimum 300 GSM) using a 1200 DPI laser engine.
2. Laminate with a matte anti-glare finish (specular reflectivity $< 4\%$).
3. Bond rigidly to the staging base plate in the lower-right quadrant, coplanar with the sample inspection plane.

---

## 4. Acoustic Resonance NDT Probe (Optional Research Subsystem)

To detect internal storage decay (*Fusarium* basal plate rot and bacterial hollow-heart) undetectable by surface optical inspection:

- **Transducer Type:** Piezoelectric contact ceramic disk ($27\text{ mm}$ diameter, brass backing).
- **Excitation:** Mechanical solenoidal pendulum delivering a calibrated $0.05\text{ J}$ tap impulse to the equatorial cheek of the bulb.
- **Audio Capture Interface:** 24-bit $44.1\text{ kHz}$ analog-to-digital converter (ADC) connected to onboard host or mobile audio line-in.
- **Signal Analysis:** 2048-point Fast Fourier Transform (FFT) with Hann windowing extracting fundamental resonance frequency $f_0$ ($400 - 1000\text{ Hz}$) and damping Quality Factor $Q$:
  $$Q = \frac{f_0}{\Delta f_{-3\text{dB}}}$$
- **Diagnostic Invariant:** Healthy firm bulbs demonstrate $f_0 > 650\text{ Hz}$ and $Q > 15$. Decomposed internal tissue manifests damped resonance ($f_0 < 450\text{ Hz}$, $Q < 8$).

---

## 5. Wiring, Host Interconnects & Power Budget

```
+------------------------------------------------------------------+
|                     CEPA Edge Station Hub                        |
|                                                                  |
|   +--------------------+              +----------------------+   |
|   |  12V 5A DC Supply  |----+-------->|  Ring Diffuser (12V) |   |
|   +--------------------+    |         +----------------------+   |
|                             |                                    |
|                             +-------->|  Buck Converter (5V) |   |
|                                       +----------+-----------+   |
|                                                  |               |
|                                                  v               |
|   +----------------------------------------------------------+   |
|   |  Host Single-Board Computer / Mandi Workstation Laptop   |   |
|   |  - USB 3.0: 1080p Optical Sensor Camera                  |   |
|   |  - USB Audio: MEMS Acoustic NDT Transducer               |   |
|   |  - Ethernet / Wi-Fi: Local APMC Subnet / Hotspot         |   |
|   |  - Thermal Budget: Fan-cooled sealed IP54 dust enclosure |   |
|   +----------------------------------------------------------+   |
+------------------------------------------------------------------+
```

Total power draw is under 25 Watts, enabling continuous 8-hour operation off a standard $12\text{V}$ 100Ah lead-acid tractor battery or portable lithium power bank during rural mandi power outages.
