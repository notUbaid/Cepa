"""
CEPA Live Production Smoke Test
Verifies all 7 core inspection pipelines against running uvicorn server on http://localhost:8000
"""
import urllib.request
import json
import io
import os
import wave
import struct
import math

BASE = os.environ.get("CEPA_API_BASE", "http://localhost:8000/api/v1")

def run_smoke_test():
    print("--- 1. Inspection Creation with AgriStack Farmer ---")
    req = urllib.request.Request(
        f"{BASE}/inspections",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "lot_id": "LOT-LIVE-HACKATHON-01",
            "procurement_centre": "Lasalgaon Mandi Yard, Nashik",
            "officer_name": "Inspector A. K. Patil",
            "variety": "Nashik Red",
            "crop_season": "Rabi 2026",
            "farmer_id": "MH-NSK-2026-88192",
            "farmer_name": "Kisan Ramesh Shinde"
        }).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        insp = json.loads(resp.read().decode("utf-8"))
    insp_id = insp["id"]
    print(f"PASSED: ID={insp_id}, Farmer={insp.get('farmer_name')}, Lot={insp['lot_id']}")

    from pathlib import Path
    img_path = Path(__file__).resolve().parent.parent / "static" / "demo_onion_spread.jpg"
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    boundary = "----WebKitFormBoundaryCePaLiveTest"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="sample.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + img_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/inspections/{insp_id}/samples",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        data=body
    )
    with urllib.request.urlopen(req) as resp:
        sample_res = json.loads(resp.read().decode("utf-8"))
    sample_id = sample_res["id"]
    print(f"PASSED: SampleID={sample_id}, OnionCount={sample_res['onion_count']}, Calibrated={sample_res['marker_detected']}")

    print("\n--- 3. Acoustic Tap Analysis ---")
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        data = bytearray()
        for i in range(4410):
            val = int(16000 * math.sin(2 * math.pi * 1000 * i / 44100))
            data.extend(struct.pack("<h", val))
        wf.writeframes(data)
    wav_bytes = wav_io.getvalue()

    ac_boundary = "----WebKitFormBoundaryAcousticTap"
    ac_body = (
        f"--{ac_boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="tap.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode("utf-8") + wav_bytes + f"\r\n--{ac_boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/inspections/{insp_id}/acoustic",
        headers={"Content-Type": f"multipart/form-data; boundary={ac_boundary}"},
        data=ac_body
    )
    with urllib.request.urlopen(req) as resp:
        ac_res = json.loads(resp.read().decode("utf-8"))
    reading = ac_res["reading"]
    print(f"PASSED: DominantFreq={reading['dominant_freq_hz']}Hz, RiskTier={reading['hollow_risk_tier']}, Conf={reading['confidence']}")

    print("\n--- 4. Flash Proxy Index (FPI) Differential Spectroscopy ---")
    import cv2
    import numpy as np
    small_img = cv2.resize(cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR), (640, 480))
    _, small_buf = cv2.imencode(".jpg", small_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    fpi_test_bytes = small_buf.tobytes()

    fpi_boundary = "----WebKitFormBoundaryFpiLive"
    fpi_body = (
        f"--{fpi_boundary}\r\n"
        f'Content-Disposition: form-data; name="ambient_file"; filename="ambient.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + fpi_test_bytes + (
        f"\r\n--{fpi_boundary}\r\n"
        f'Content-Disposition: form-data; name="flash_file"; filename="flash.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + fpi_test_bytes + f"\r\n--{fpi_boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}/inspections/{insp_id}/fpi",
        headers={"Content-Type": f"multipart/form-data; boundary={fpi_boundary}"},
        data=fpi_body
    )
    with urllib.request.urlopen(req) as resp:
        fpi_res = json.loads(resp.read().decode("utf-8"))
    print(f"PASSED: MeanFPI={fpi_res['mean_fpi']:.3f}, SurfaceState={fpi_res['surface_state']}, HeatmapBytes={len(fpi_res['heatmap_base64'])}")

    print("\n--- 5. eNAM v2.1 Assaying Integration (JSON & XML) ---")
    with urllib.request.urlopen(f"{BASE}/inspections/{insp_id}/enam?format=json") as resp:
        enam_json = json.loads(resp.read().decode("utf-8"))
    payload = enam_json["payload_json"]
    print(f"PASSED JSON: Schema={payload['schema_version']}, Farmer={payload['farmer_profile']['farmer_name']}, LotWeight={payload['consignment']['declared_weight_kg']}kg")

    with urllib.request.urlopen(f"{BASE}/inspections/{insp_id}/enam?format=xml") as resp:
        xml_data = resp.read().decode("utf-8")
    assert "<AgriStackFarmerID>MH-NSK-2026-88192</AgriStackFarmerID>" in xml_data
    assert "<eNAMAssayingCertificate" in xml_data
    print(f"PASSED XML: Length={len(xml_data)} chars, Verified AgriStack Farmer tag present")

    print("\n--- 6. Finalization & Official Grade Assignment ---")
    req = urllib.request.Request(
        f"{BASE}/inspections/{insp_id}/finalize",
        headers={"Content-Type": "application/json"},
        data=b"{}"
    )
    with urllib.request.urlopen(req) as resp:
        fin_res = json.loads(resp.read().decode("utf-8"))
    print(f"PASSED: Status={fin_res['status']}, Grade_A={fin_res['grade_a_pct']:.1f}%, URS={fin_res['urs_pct']:.1f}%, Rejected={fin_res['rejected_pct']:.1f}%")

    print("\n--- 7. PDF Assaying Certificate Generation (ReportLab) ---")
    with urllib.request.urlopen(f"{BASE}/inspections/{insp_id}/reports/pdf") as resp:
        pdf_bytes = resp.read()
    assert pdf_bytes.startswith(b"%PDF"), "Must be a valid PDF file binary!"
    print(f"PASSED PDF: Rendered {len(pdf_bytes)} bytes without errors, starts with %PDF header")

    print("=======================================================")
    print("[SUCCESS] ALL 7 PRODUCTION WORKFLOW TESTS COMPLETED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    run_smoke_test()
