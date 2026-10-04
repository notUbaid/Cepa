"""
Groq Generative AI Agronomist Service

Harnesses Groq's high-speed multimodal Vision and Text LLM (qwen/qwen3.8-27b)
to deliver human-understandable, expert post-harvest onion quality appraisals,
pathology identification (Aspergillus niger, neck rot, sprouting),
and interactive agronomic advice for farmers and APMC mandi officers.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import urllib.request
from typing import Any

import cv2
import numpy as np

from config import settings

logger = logging.getLogger(__name__)

GROQ_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_VISION_MODEL = getattr(settings, "groq_vision_model", "qwen/qwen3.8-27b")
GROQ_TEXT_MODEL = getattr(settings, "groq_text_model", "qwen/qwen3.8-27b")


def _get_groq_api_key() -> str:
    """Retrieve Groq API key from environment variable or settings."""
    return os.environ.get("GROQ_API_KEY") or getattr(settings, "groq_api_key", "")


def _make_groq_request(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute a request to Groq API with proper headers and error handling."""
    api_key = _get_groq_api_key()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured")

    req = urllib.request.Request(
        GROQ_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Cepa-Mandi-AI/1.0",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    with urllib.request.urlopen(req, timeout=12.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def analyze_inspection_with_ai(image_bgr: np.ndarray) -> dict[str, Any]:
    """
    Run Multimodal Generative Vision AI on an onion inspection image.

    Args:
        image_bgr: BGR uint8 OpenCV image.

    Returns:
        Structured dictionary with human verdict, defects, storage advice, and quality rating.
    """
    try:
        # Resize image for ultra-fast network transfer (512px max dimension)
        h, w = image_bgr.shape[:2]
        max_dim = 512
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            resized = cv2.resize(image_bgr, (int(w * scale), int(h * scale)))
        else:
            resized = image_bgr

        _, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
        b64_image = base64.b64encode(buf).decode("utf-8")

        prompt = (
            "You are an expert Indian Agricultural Officer and post-harvest Onion Pathologist. "
            "Examine this photo of onion bulbs. "
            "Provide your findings in clean JSON format with these exact keys:\n"
            "{\n"
            '  "quality_rating": "EXCELLENT" | "GOOD" | "FAIR" | "POOR",\n'
            '  "summary_verdict": "2 short, friendly, plain-English sentences for a farmer explaining overall quality",\n'
            '  "defects_observed": ["list of specific defects spotted, e.g. active neck sprout, soft rot, papery peel missing, or None if healthy"],\n'
            '  "storage_advice": "Actionable, simple storage instructions (e.g. how many days it will keep, ventilation needs)",\n'
            '  "fair_market_note": "A brief commercial pricing guidance note based on physical appearance"\n'
            "}\n"
            "Return ONLY the JSON object, nothing else."
        )

        payload = {
            "model": GROQ_VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                }
            ],
            "max_tokens": 400,
            "temperature": 0.2,
        }

        resp = _make_groq_request(payload)
        content = resp["choices"][0]["message"]["content"].strip()

        # Clean JSON markdown fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        parsed = json.loads(content)
        parsed["powered_by"] = f"Groq AI ({GROQ_VISION_MODEL})"
        parsed["available"] = True
        logger.info("Groq Vision AI successfully appraised inspection image.")
        return parsed

    except Exception as e:
        logger.warning("Groq Vision AI unavailable: %s", e)
        return {
            "available": False,
            "powered_by": "Cepa Offline (Groq unavailable)",
            "error": "AI agronomist is not available. Configure GROQ_API_KEY to enable real-time analysis.",
        }


def ask_ai_agronomist_detailed(question: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Detailed Q&A with the Groq AI Agronomist, returning answer, powered_by label, and fallback status.
    """
    try:
        system_prompt = (
            "You are Cepa AI Agronomist, a helpful, friendly, and expert agricultural advisor "
            "for Indian onion farmers and mandi procurement officers. "
            "You explain things simply and practically without confusing academic jargon. "
            "Give direct, helpful advice on shelf-life, rot prevention, fair mandi prices, and grading."
        )

        avg_diam = context.get("avg_diameter_mm")
        avg_diam_str = f"{avg_diam} mm" if avg_diam is not None else "Not measured"
        net_rate_val = context.get("net_rate_inr")
        net_rate_str = f"₹{net_rate_val} / quintal" if net_rate_val is not None else "Pending assessment"
        storage_val = context.get("storage_days")
        storage_str = f"{storage_val} days" if storage_val is not None else "Pending appraisal"

        user_content = (
            f"Here is the data about this onion lot:\n"
            f"- Total Bulbs Checked: {context.get('total_bulbs', 0)}\n"
            f"- Grade A (Top Quality): {context.get('grade_a_count', 0)}\n"
            f"- URS (Usable/Minor defects): {context.get('urs_count', 0)}\n"
            f"- Rejected (Rotten/Sprouted): {context.get('rejected_count', 0)}\n"
            f"- Mean Caliber Diameter: {avg_diam_str}\n"
            f"- Estimated Payout Rate: {net_rate_str}\n"
            f"- Expected Storage Horizon: {storage_str}\n\n"
            f"User Question: {question}\n\n"
            f"Please give a clear, direct, and actionable answer in 2-3 friendly paragraphs."
        )

        payload = {
            "model": GROQ_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 350,
            "temperature": 0.3,
        }

        resp = _make_groq_request(payload)
        content = resp["choices"][0]["message"]["content"].strip()
        return {
            "answer": content,
            "powered_by": f"Groq AI ({GROQ_TEXT_MODEL})",
            "is_fallback": False,
        }

    except Exception as e:
        logger.warning("Groq AI Agronomist chat fallback: %s", e)
        total = context.get("total_bulbs", 0)
        grade_a = context.get("grade_a_count", 0)
        rejected = context.get("rejected_count", 0)
        storage_days = context.get("storage_days")
        net_rate = context.get("net_rate_inr")

        storage_clause = f"for prolonged buffer storage ({storage_days} days)" if storage_days else "for prolonged buffer storage"
        storage_hold = f"for up to {storage_days} days" if storage_days else "for seasonal holding"
        storage_strat = f"for up to {storage_days} days" if storage_days else "for strategic buffer storage"
        payout_clause = f"at the adjusted procurement rate of approximately ₹{net_rate}/quintal" if net_rate else "at the adjusted APMC procurement rate"
        payout_clean = f"at ₹{net_rate}/quintal" if net_rate else "at benchmark APMC rates"
        payout_fair = f"₹{net_rate}/quintal" if net_rate else "assessed APMC realization"

        if total == 0:
            text = (
                "[Rule-Based Offline Advisory]: No inspection measurements or bulb instances are currently recorded for this lot. "
                "Please capture and process a top-down produce sample spread to generate objective quality metrics, "
                "caliper diameters, and shelf-life forecasts."
            )
        elif rejected > 0 and (rejected / total) > 0.15:
            text = (
                f"[Rule-Based Offline Advisory]: High rot/defect concentration detected ({rejected} of {total} bulbs rejected). "
                f"This lot is NOT recommended {storage_clause}. "
                "Immediate segregation and culling is strongly advised to prevent soft rot or black mold "
                "from contaminating adjacent stock. We recommend routing this lot for immediate auction "
                f"{payout_clause}."
            )
        elif rejected > 0:
            text = (
                f"[Rule-Based Offline Advisory]: Fair quality lot with {grade_a} Grade A bulbs out of {total} sampled. "
                f"However, {rejected} rejected/decayed bulb(s) must be culled manually prior to storage. "
                f"With thorough culling and well-ventilated crate storage (25–30°C, RH 65–70%), this lot can be safely held "
                f"{storage_hold}. Net estimated realization: {payout_fair}."
            )
        else:
            text = (
                f"[Rule-Based Offline Advisory]: Excellent quality lot with zero critical defects across {total} inspected bulbs ({grade_a} Grade A). "
                f"Tunics are sound and suitable for strategic buffer storage {storage_strat}. "
                "Store on raised slatted bamboo racks or aerated plastic crates with bottom airflow to prevent moisture accumulation. "
                f"Approved for full MSP/benchmark payout {payout_clean}."
            )

        return {
            "answer": text,
            "powered_by": "Cepa Mandi Rule Engine (Offline Fallback)",
            "is_fallback": True,
        }


def ask_ai_agronomist(question: str, context: dict[str, Any]) -> str:
    """
    Interactive Q&A with the Groq AI Agronomist about an inspection lot.
    Backward-compatible wrapper returning answer string.
    """
    res = ask_ai_agronomist_detailed(question, context)
    return res["answer"]
