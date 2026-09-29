import urllib.request
import json
import os

BASE_URL = "http://localhost:8000"

def test_full_pipeline():
    # 1. Create inspection
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "lot_id": "LOT-E2E-PERFECT-01",
            "procurement_centre": "Lasalgaon Mandi Yard, Nashik",
            "officer_name": "Senior Inspector Patil",
            "officer_id": "APMC-NAS-8821",
            "notes": "Production verification test for Grade A single red onion"
        }).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        insp = json.loads(resp.read().decode("utf-8"))
    insp_id = insp["id"]
    print("1. Created Inspection:", insp_id, insp["lot_id"])

    # 2. Upload single_red_onion.jpg
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    with open("test_images/single_red_onion.jpg", "rb") as f:
        img_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="single_red_onion.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + img_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections/{insp_id}/samples",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        data=body
    )
    with urllib.request.urlopen(req) as resp:
        sample = json.loads(resp.read().decode("utf-8"))
    print("2. Sample Processed:")
    print("   Status:", sample["processing_status"], "Quality Passed:", sample["quality_passed"])
    print("   Onions Count:", sample["onion_count"], "Scale:", sample["scale_mm_per_px"])

    # Fetch updated inspection
    with urllib.request.urlopen(f"{BASE_URL}/api/v1/inspections/{insp_id}") as resp:
        insp_detail = json.loads(resp.read().decode("utf-8"))
    print("   Lot Aggregation -> Total:", insp_detail["total_bulbs"], "Grade A:", insp_detail["grade_a_count"], "URS:", insp_detail["urs_count"], "Rejected:", insp_detail["rejected_count"])

    # 3. Ask Groq AI Agronomist
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections/{insp_id}/ask-ai",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"question": "Is this onion Grade A quality for export?"}).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        ai_ans = json.loads(resp.read().decode("utf-8"))
    print("3. Groq AI Agronomist Response:")
    print("   Answer snippet:", ai_ans["answer"][:160] + "...")

    # 4. Finalize inspection
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections/{insp_id}/finalize",
        headers={"Content-Type": "application/json"},
        data=b"{}"
    )
    with urllib.request.urlopen(req) as resp:
        finalized = json.loads(resp.read().decode("utf-8"))
    print("4. Finalized:", finalized["status"])

    # 5. Generate Report & PDF
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections/{insp_id}/reports",
        headers={"Content-Type": "application/json"},
        data=b"{}"
    )
    with urllib.request.urlopen(req) as resp:
        rep = json.loads(resp.read().decode("utf-8"))
    print("5. Report Generated:", rep["report_id"], "Share URL:", rep["share_url"])

    # 6. Check PDF download
    with urllib.request.urlopen(f"{BASE_URL}/api/v1/inspections/{insp_id}/reports/pdf") as resp:
        pdf_bytes = resp.read()
    print("6. PDF Downloaded: Size =", len(pdf_bytes), "bytes (Starts with %PDF:", pdf_bytes.startswith(b"%PDF"), ")")

    # 7. Check public share HTML page
    with urllib.request.urlopen(rep["share_url"]) as resp:
        html = resp.read().decode("utf-8")
    print("7. Public Share Page: Length =", len(html), "chars (Contains 'LOT-E2E-PERFECT-01':", "LOT-E2E-PERFECT-01" in html, ")")

if __name__ == "__main__":
    test_full_pipeline()
