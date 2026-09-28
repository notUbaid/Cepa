import urllib.request
import json
import socket
import pytest

BASE_URL = "http://localhost:8000"

def _is_server_running() -> bool:
    try:
        s = socket.create_connection(("localhost", 8000), timeout=0.3)
        s.close()
        return True
    except Exception:
        return False

@pytest.mark.skipif(not _is_server_running(), reason="Requires live uvicorn backend running on localhost:8000")
def test_video_scan():
    # Create inspection
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "lot_id": "LOT-VIDEO-PERFECT-01",
            "procurement_centre": "Lasalgaon Mandi Yard, Nashik",
            "officer_name": "Inspector Patil"
        }).encode("utf-8")
    )
    with urllib.request.urlopen(req) as resp:
        insp = json.loads(resp.read().decode("utf-8"))
    insp_id = insp["id"]

    # Upload video
    boundary = "----WebKitFormBoundaryVideo123"
    from pathlib import Path
    video_path = Path(__file__).parent.parent / "storage" / "demo_onion_sweep.mp4"
    if not video_path.exists():
        video_path = Path("storage") / "demo_onion_sweep.mp4"
    with open(video_path, "rb") as f:
        video_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="demo_sweep.mp4"\r\n'
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + video_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/inspections/{insp_id}/video",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        data=body
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    print("Video Scan Success!")
    print("Sample ID:", res["sample_id"])
    print("Duration sec:", res["duration_seconds"], "Keyframes sampled:", res["keyframes_sampled"])
    print("Total bulbs spotted:", res["total_bulbs_spotted"], "Healthy:", res["healthy_bulbs_count"], "Bad:", res["bad_bulbs_count"])
    print("Health score:", res["health_score"], "Status:", res["overall_status"])
    print("AI Verdict:", res["ai_agronomist_verdict"].get("quality_rating"))
    print("AI Summary:", res["ai_agronomist_verdict"].get("summary_verdict")[:140] + "...")

if __name__ == "__main__":
    test_video_scan()
