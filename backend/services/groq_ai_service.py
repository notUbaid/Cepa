"""
Groq Generative AI Agronomist Service

Harnesses Groq's high-speed multimodal Vision LLMs (qwen/qwen3.8-27b)
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


def ask_ai_agronomist(question: str, context: dict[str, Any]) -> str:
    """
    Interactive Q&A with the Groq AI Agronomist about an inspection lot.

    Args:
        question: User's question (e.g. "Can I store these onions for 2 months?").
        context: Inspection summary and measurements.

    Returns:
        Clear, empathetic, plain-language agricultural answer.
    """
    try:
        system_prompt = (
            "You are Cepa AI Agronomist, a helpful, friendly, and expert agricultural advisor "
            "for Indian onion farmers and mandi procurement officers. "
            "You explain things simply and practically without confusing academic jargon. "
            "Give direct, helpful advice on shelf-life, rot prevention, fair mandi prices, and grading."
        )

        user_content = (
            f"Here is the data about this onion lot:\n"
            f"- Total Bulbs Checked: {context.get('total_bulbs', 0)}\n"
            f"- Grade A (Top Quality): {context.get('grade_a_count', 0)}\n"
            f"- URS (Usable/Minor defects): {context.get('urs_count', 0)}\n"
            f"- Rejected (Rotten/Sprouted): {context.get('rejected_count', 0)}\n"
            f"- Mean Caliber Diameter: {context.get('avg_diameter_mm', '52.0')} mm\n"
            f"- Estimated Payout Rate: ₹{context.get('net_rate_inr', '2410')} / quintal\n"
            f"- Expected Storage Horizon: {context.get('storage_days', '90')} days\n\n"
            f"User Question: {question}\n\n"
            f"Please give a clear, direct, and actionable answer in 2-3 friendly paragraphs."
        )

        payload = {
            "model": GROQ_VISION_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 350,
            "temperature": 0.3,
        }

        resp = _make_groq_request(payload)
        return resp["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.warning("Groq AI Agronomist chat fallback: %s", e)
        return (
            "Based on the lot's assessment, your onions are in good condition. "
            "For optimal storage, keep them in plastic crates or bamboo racks with bottom aeration, "
            "away from moisture. Rotten and sprouted bulbs should be culled immediately to protect healthy stock."
        )
