"""
Cepa Public HTML Certificate Generator.

Renders an official, responsive digital quality verification certificate for
scanned QR codes on printed mandi slips and reports.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
from typing import Any

from config import settings
from services.report_generator import _get_policy_verified


def _e(value: object) -> str:
    """HTML-escape a value for safe interpolation into the certificate template."""
    return _html.escape(str(value) if value is not None else "")


def render_certificate_html(report_detail: Any, inspection: Any) -> str:
    """
    Generate responsive HTML certificate for public verification.
    """
    r = report_detail
    from services.crypto_seal import compute_inspection_seal
    cert_seal, img_sha256 = compute_inspection_seal(r, inspection)

    policy_version = getattr(r, "ruleset_version", "DEMO_ASSUMPTION_v1")
    is_policy_verified = _get_policy_verified(policy_version)
    is_mock = getattr(settings, "def_use_mock", True)
    is_provisional = (not is_policy_verified) or is_mock

    provisional_banner_html = ""
    if is_provisional:
        provisional_banner_html = f"""
        <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-radius: 12px; padding: 14px 18px; color: #fca5a5; font-size: 13px; line-height: 1.5;">
          <div style="font-weight: 700; color: #f87171; font-size: 14px; margin-bottom: 4px; display: flex; align-items: center; gap: 8px;">
            <span>[WARN]</span> PROVISIONAL RECORD -- UNVERIFIED INPUTS
          </div>
          <div>This certificate was evaluated under working policy <strong>{_e(policy_version)}</strong> (verified: {_e(is_policy_verified)}) and rule-based mock defect scores (DEF_USE_MOCK={_e(is_mock)}). It is an academic prototype artifact and <strong>not legally binding for commercial APMC settlement</strong>.</div>
        </div>
        """

    storage_adv = getattr(r, "storage_advisory", None) or {}
    storage_score = storage_adv.get("mean_storageability_score", 85.0)
    storage_rec = storage_adv.get("storage_recommendation", "STANDARD_COLD_STORAGE").replace("_", " ")
    storage_days = storage_adv.get("recommended_max_storage_days", 60)
    storage_risk = storage_adv.get("respiration_risk_level", "LOW")
    storage_action = storage_adv.get("recommended_action", "Store in well-ventilated crates.")

    settlement = getattr(r, "commercial_settlement", None) or {}
    base_msp = settlement.get("base_msp_inr_per_qtl", 2410.0)
    net_rate = settlement.get("net_payout_rate_inr_per_qtl", 2410.0)
    total_dockage = settlement.get("total_dockage_inr_per_qtl", 0.0)
    tier = settlement.get("settlement_tier", "FULL_MSP_PAYOUT").replace("_", " ")
    gross_payout = settlement.get("estimated_gross_payout_inr", base_msp * 50)
    net_payout = settlement.get("estimated_net_payout_inr", net_rate * 50)
    dockage_items = settlement.get("dockage_items", [])

    # Find annotated image URL from first sample if available
    annotated_img_url = ""
    scale_mm = ""
    for s in inspection.samples:
        if s.processed_image_path:
            annotated_img_url = f"/api/v1/storage/{_e(s.processed_image_path)}?token={_e(r.share_token)}"
        elif s.image_path:
            annotated_img_url = f"/api/v1/storage/{_e(s.image_path)}?token={_e(r.share_token)}"
        if s.scale_mm_per_px:
            scale_mm = f"{s.scale_mm_per_px:.4f} mm/px (ChArUco 7x5 locked)"
        if annotated_img_url:
            break

    # H6 privacy: Public share links should not broadcast exact meter-level GPS or raw officer credentials
    raw_officer_id = str(r.officer_id or "").strip()
    if len(raw_officer_id) > 4:
        masked_officer_id = f"***-{raw_officer_id[-4:]}"
    elif raw_officer_id:
        masked_officer_id = "***"
    else:
        masked_officer_id = "--"

    # Truncate to ~1.1km precinct resolution (2 decimal places) for public privacy
    location_str = (
        f"{inspection.geo_lat:.2f}° N, {inspection.geo_lon:.2f}° E (APMC Mandi Precinct)"
        if (inspection.geo_lat is not None and inspection.geo_lon is not None)
        else "Location unrecorded"
    )

    # Escaped versions of user-controlled report/inspection fields
    lot_id_safe = _e(r.lot_id or "N/A")
    centre_safe = _e(r.procurement_centre or "N/A")
    officer_name_safe = _e(r.officer_name or "N/A")
    officer_id_safe = _e(masked_officer_id)
    ruleset_safe = _e(r.ruleset_version)
    policy_version_safe = _e(policy_version)
    storage_rec_safe = _e(storage_rec)
    storage_risk_safe = _e(storage_risk)
    storage_action_safe = _e(storage_action)
    tier_safe = _e(tier)

    # Format dockage rows — escape the user-supplied title field
    dockage_rows_html = ""
    if dockage_items:
        for it in dockage_items:
            dockage_rows_html += f"""
            <tr>
              <td>{_e(it.get('title', ''))}</td>
              <td style="text-align:center">{it.get('measured_pct', 0.0):.1f}%</td>
              <td style="text-align:center">{it.get('permissible_limit_pct', 0.0):.1f}%</td>
              <td style="text-align:right; color:#ef4444; font-weight:600">-₹{it.get('deduction_inr_per_qtl', 0.0):.1f}</td>
            </tr>
            """
    else:
        dockage_rows_html = """
        <tr>
          <td colspan="4" style="text-align:center; color:#22c55e; padding:12px 0;">
            [PASS] Zero FAQ off-grade dockage. Full standard met.
          </td>
        </tr>
        """

    pdf_href = f"/api/v1/inspections/{_e(inspection.id)}/reports/pdf"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <title>Cepa -- Verified Mandi Lot Certificate #{r.report_id[:8]}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #09090b;
      --card-bg: #121215;
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f4f4f5;
      --text-muted: #a1a1aa;
      --text-dim: #71717a;
      --accent: #10b981;
      --accent-bg: rgba(16, 185, 129, 0.1);
      --grade-a: #10b981;
      --urs: #f59e0b;
      --reject: #ef4444;
      --font: 'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif;
      --mono: 'JetBrains Mono', monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      line-height: 1.5;
      padding: 16px;
      display: flex;
      justify-content: center;
    }}
    .cert-container {{
      max-width: 680px;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .header-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .brand-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .brand-left {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .brand-logo {{
      width: 36px;
      height: 36px;
      border-radius: 8px;
      background: #000;
      border: 1px solid rgba(255,255,255,0.15);
      object-fit: contain;
    }}
    .brand-title {{
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .brand-sub {{
      font-size: 11px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .verified-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent-bg);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 600;
      font-family: var(--mono);
    }}
    .pulse-dot {{
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--accent);
      box-shadow: 0 0 8px var(--accent);
    }}
    .hash-banner {{
      background: rgba(255,255,255,0.03);
      border-radius: 8px;
      padding: 8px 12px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      font-family: var(--mono);
      font-size: 11px;
      color: var(--text-dim);
    }}
    .hash-val {{
      color: var(--text-muted);
      font-weight: 500;
    }}
    .section-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .section-title {{
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      border-bottom: 1px solid rgba(255,255,255,0.06);
      padding-bottom: 8px;
    }}
    .data-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    @media (max-width: 480px) {{
      .data-grid {{ grid-template-columns: 1fr; }}
    }}
    .data-item {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .data-label {{
      font-size: 11px;
      color: var(--text-dim);
    }}
    .data-value {{
      font-size: 14px;
      font-weight: 600;
      color: var(--text);
    }}
    .data-value-mono {{
      font-family: var(--mono);
      font-size: 12.5px;
      color: var(--text);
    }}
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }}
    .kpi-box {{
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .kpi-box-val {{
      font-size: 18px;
      font-weight: 700;
    }}
    .kpi-box-lbl {{
      font-size: 11px;
      color: var(--text-dim);
    }}
    .table-custom {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12.5px;
    }}
    .table-custom th {{
      text-align: left;
      color: var(--text-dim);
      font-weight: 500;
      padding: 6px 8px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      font-size: 11px;
      text-transform: uppercase;
    }}
    .table-custom td {{
      padding: 8px;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      color: var(--text);
    }}
    .payout-highlight {{
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .payout-rate-box {{
      display: flex;
      flex-direction: column;
    }}
    .payout-rate-lbl {{
      font-size: 11px;
      color: var(--accent);
      font-weight: 600;
      text-transform: uppercase;
    }}
    .payout-rate-val {{
      font-size: 22px;
      font-weight: 700;
      color: #fff;
    }}
    .payout-total-val {{
      font-size: 14px;
      color: var(--text-muted);
      font-family: var(--mono);
    }}
    .storage-box {{
      background: rgba(255,255,255,0.02);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .storage-score-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .storage-score-num {{
      font-size: 24px;
      font-weight: 700;
      color: var(--accent);
      font-family: var(--mono);
    }}
    .advisory-text {{
      font-size: 12.5px;
      color: var(--text-muted);
      line-height: 1.4;
    }}
    .img-card {{
      width: 100%;
      border-radius: 10px;
      border: 1px solid var(--card-border);
      max-height: 380px;
      object-fit: cover;
      background: #000;
    }}
    .btn-row {{
      display: flex;
      gap: 10px;
    }}
    .btn-primary {{
      flex: 1;
      background: var(--text);
      color: #000;
      font-weight: 600;
      font-size: 13.5px;
      padding: 12px 18px;
      border-radius: 10px;
      text-align: center;
      text-decoration: none;
      display: inline-block;
      transition: opacity 0.15s;
    }}
    .btn-primary:hover {{ opacity: 0.9; }}
    .btn-secondary {{
      background: rgba(255,255,255,0.06);
      color: var(--text);
      font-weight: 500;
      font-size: 13.5px;
      padding: 12px 18px;
      border-radius: 10px;
      text-align: center;
      text-decoration: none;
      cursor: pointer;
      border: 1px solid var(--card-border);
    }}
    .footer-note {{
      font-size: 11px;
      color: var(--text-dim);
      text-align: center;
      padding: 8px 0 16px;
    }}
  </style>
</head>
  <div class="cert-container">

    {provisional_banner_html}

    <!-- Header Certificate Card -->
    <div class="header-card">
      <div class="brand-row">
        <div class="brand-left">
          <img src="/ui/logo.png" alt="Cepa" class="brand-logo" onerror="this.style.display='none'" />
          <div>
            <div class="brand-title">Cepa Mandi Procurement Record</div>
            <div class="brand-sub">Government of India - APMC Quality Protocol</div>
          </div>
        </div>
        <div class="verified-badge" style="{'background:rgba(245,158,11,0.15); border-color:#f59e0b; color:#fbbf24;' if is_provisional else ''}">
          <span class="pulse-dot" style="{'background:#f59e0b;' if is_provisional else ''}"></span> {'PROVISIONAL' if is_provisional else 'VERIFIED'}
        </div>
      </div>

      <div class="hash-banner" style="display: flex; flex-direction: column; gap: 4px; padding: 12px 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; letter-spacing: 0.05em; font-size: 11px;">SOVEREIGN CRYPTOGRAPHIC SEAL:</span>
          <a href="/api/v1/reports/{getattr(r, 'report_id', '')}/verify" style="color: #38bdf8; font-size: 11px; text-decoration: underline;" target="_blank">Verify Mathematical Proof &rarr;</a>
        </div>
        <span class="hash-val" style="font-size: 11px; word-break: break-all; font-family: monospace; line-height: 1.4;">HMAC-SHA256:{cert_seal}</span>
      </div>
    </div>

    <!-- Consignment Details -->
    <div class="section-card">
      <div class="section-title">Consignment Metadata · लॉट तपशील</div>
      <div class="data-grid">
        <div class="data-item">
          <span class="data-label">Lot Identifier · लॉट क्र.</span>
          <span class="data-value">{lot_id_safe}</span>
        </div>
        <div class="data-item">
          <span class="data-label">APMC Mandi / Centre · कृषी उत्पन्न बाजार समिती</span>
          <span class="data-value">{centre_safe}</span>
        </div>
        <div class="data-item">
          <span class="data-label">Authorized Grading Officer · तपासणी अधिकारी</span>
          <span class="data-value">{officer_name_safe} ({officer_id_safe})</span>
        </div>
        <div class="data-item">
          <span class="data-label">Grading Specification Standard · निकष</span>
          <span class="data-value-mono">{ruleset_safe} (BIS IS 17912:2022)</span>
        </div>
        <div class="data-item">
          <span class="data-label">Sample Bulbs Assessed · मोजलेले कांदे</span>
          <span class="data-value">{r.total_bulbs} verified onion instances</span>
        </div>
        <div class="data-item">
          <span class="data-label">Optical Scale Calibration · प्रमाणन</span>
          <span class="data-value-mono">{_e(scale_mm) or 'ChArUco 7x5 Active'}</span>
        </div>
        <div class="data-item">
          <span class="data-label">Device-Reported Location (Unverified GNSS) · साधन-नोंदणीकृत स्थान</span>
          <span class="data-value">{_e(location_str)}</span>
        </div>
      </div>
    </div>

    <!-- Quality Grade Distribution -->
    <div class="section-card">
      <div class="section-title">Agronomic Lot Grade Distribution · गुणवत्ता प्रतवारी</div>
      <div class="kpi-row">
        <div class="kpi-box" style="border: 1px solid rgba(16, 185, 129, 0.25); background: rgba(16, 185, 129, 0.04);">
          <span class="kpi-box-val" style="color:var(--grade-a);">{r.grade_a_pct:.1f}%</span>
          <span class="kpi-box-lbl">Grade A · दर्जा 'अ' ({r.grade_a_count} bulbs)</span>
          <span style="font-size:10px; color:var(--text-dim);">45-65 mm target (सुपर)</span>
        </div>
        <div class="kpi-box" style="border: 1px solid rgba(245, 158, 11, 0.25); background: rgba(245, 158, 11, 0.04);">
          <span class="kpi-box-val" style="color:var(--urs);">{r.urs_pct:.1f}%</span>
          <span class="kpi-box-lbl">URS · शिथिल निकष ({r.urs_count} bulbs)</span>
          <span style="font-size:10px; color:var(--text-dim);">35-70 mm relaxed (मध्यम)</span>
        </div>
        <div class="kpi-box" style="border: 1px solid rgba(239, 68, 68, 0.25); background: rgba(239, 68, 68, 0.04);">
          <span class="kpi-box-val" style="color:var(--reject);">{r.rejected_pct:.1f}%</span>
          <span class="kpi-box-lbl">Rejected · अमान्य ({r.rejected_count} bulbs)</span>
          <span style="font-size:10px; color:var(--text-dim);">Rot / &lt;35 mm (रद्द / गोली)</span>
        </div>
      </div>
    </div>

    <!-- Cold Storage Shelf-Life & Storageability Advisory -->
    <div class="section-card">
      <div class="section-title">Post-Harvest Cold Storage Preservation Advisory · शीतगृह साठवणूक सल्ला</div>
      <div class="storage-box">
        <div class="storage-score-row">
          <div>
            <div style="font-size:11px; color:var(--text-dim); text-transform:uppercase;">Storageability Score · साठवणूक निर्देशांक</div>
            <div style="font-size:15px; font-weight:600; color:#fff;">{storage_rec_safe}</div>
          </div>
          <div class="storage-score-num">{storage_score:.0f}<span style="font-size:13px; color:var(--text-dim);">/100</span></div>
        </div>
        <div class="data-grid" style="margin-top:6px;">
          <div class="data-item">
            <span class="data-label">Recommended Cold Storage Window · सुरक्षित कालावधी</span>
            <span class="data-value" style="color:var(--accent);">Up to {storage_days} Days (दिवस)</span>
          </div>
          <div class="data-item">
            <span class="data-label">Respiration &amp; Spoilage Risk · सडण्याचा धोका</span>
            <span class="data-value">{storage_risk_safe}</span>
          </div>
        </div>
        <div class="advisory-text" style="border-top:1px solid rgba(255,255,255,0.06); padding-top:8px;">
          <b>NAFED Directive (मार्गदर्शक सूचना):</b> {storage_action_safe}
        </div>
      </div>
    </div>

    <!-- Commercial Mandi Settlement Slip -->
    <div class="section-card">
      <div class="section-title">NAFED Mandi Commercial Settlement Voucher (Illustrative Simulation) · बाजार भाव व हिशोब पावती</div>
      <div class="payout-highlight">
        <div class="payout-rate-box">
          <span class="payout-rate-lbl">Net Procurement Rate (Illustrative) · निव्वळ खरेदी दर</span>
          <span class="payout-rate-val">₹{net_rate:.1f} <span style="font-size:14px; font-weight:400; color:var(--text-muted);">/ quintal (प्रति क्विंटल)</span></span>
        </div>
        <div style="text-align:right;">
          <div style="font-size:11px; color:var(--text-dim);">Est. Payout (50 qtl) · अंदाजे एकूण रक्कम</div>
          <div class="payout-total-val">₹{net_payout:,.0f}</div>
          <div style="font-size:10px; color:var(--accent);">{tier_safe}</div>
        </div>
      </div>

      <div style="margin-top:10px;">
        <div style="font-size:11px; color:var(--text-dim); margin-bottom:6px; text-transform:uppercase;">Itemized FAQ Dockage Deductions · गुणवत्ता कपात तपशील (Dockage)</div>
        <table class="table-custom">
          <thead>
            <tr>
              <th>Deduction Parameter · निकष</th>
              <th style="text-align:center">Measured · आढळलेले</th>
              <th style="text-align:center">Permissible · अनुज्ञेय</th>
              <th style="text-align:right">Deduction · कपात</th>
            </tr>
          </thead>
          <tbody>
            {dockage_rows_html}
            <tr style="border-top: 1px solid rgba(255,255,255,0.1); font-weight:600;">
              <td>Benchmark Procurement Rate (PSF/Market-Linked) [Illustrative] · आधारभूत खरेदी दर (प्रतीकात्मक)</td>
              <td colspan="2"></td>
              <td style="text-align:right">₹{base_msp:.1f}/qtl</td>
            </tr>
            <tr style="font-weight:700;">
              <td>Total FAQ Dockage Applied · एकूण कपात</td>
              <td colspan="2"></td>
              <td style="text-align:right; color:#ef4444;">-₹{total_dockage:.1f}/qtl</td>
            </tr>
          </tbody>
        </table>
        <div style="font-size:10.5px; color:var(--text-dim); margin-top:8px; line-height:1.4;">
          * Illustrative simulation based on configurable tender parameters. Onion has no statutory Minimum Support Price (MSP); procurement operates under the Price Stabilisation Fund (PSF) at market-linked benchmark rates.
        </div>
      </div>
    </div>

    <!-- High-Resolution Inspection Visual Evidence -->
    {f'''
    <div class="section-card">
      <div class="section-title">Optical Verification Evidence (ChArUco Calibrated)</div>
      <img src="{annotated_img_url}" alt="Annotated Inspection Lot" class="img-card" />
      <div style="font-size:11px; color:var(--text-dim); text-align:center;">
        Computer vision segmentation overlay: Cyan reticle = equatorial axis - Magenta = polar axis.
      </div>
    </div>
    ''' if annotated_img_url else ''}

    <!-- Action Buttons -->
    <div class="btn-row">
      <a href="{pdf_href}" class="btn-primary" target="_blank">Download Official Signed PDF</a>
      <button onclick="window.print()" class="btn-secondary">Print Voucher</button>
    </div>

    <div class="footer-note">
      Cepa National Produce Quality & Cold Storage Platform - SIH26031 Proof of Concept<br/>
      Policy: <strong>{policy_version}</strong> (verified: {is_policy_verified}) - Segmentation: <strong>YOLO11n-seg</strong> - Defect Model: <strong>{'Mock/Rule-based (DEF_USE_MOCK=true)' if is_mock else 'MobileNetV3 PyTorch'}</strong><br/>
      Cryptographic Seal: <code style="word-break: break-all;">HMAC-SHA256:{cert_seal}</code><br/>
      Photo Optical Digest: <code style="word-break: break-all;">SHA256:{img_sha256}</code> · <a href="/api/v1/reports/{getattr(r, 'report_id', '')}/verify" style="color: #38bdf8;" target="_blank">[Independent Tamper Audit]</a><br/>
      (Cryptographically binds sample photo, inspecting officer credential, and quality grading distribution)
    </div>

  </div>
</body>
</html>
"""
