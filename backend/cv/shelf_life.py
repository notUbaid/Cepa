"""
Cepa Cold Storage Storageability Index & Post-Harvest Shelf-Life Predictor.

Grounded in ICAR-DOGR (Directorate of Onion and Garlic Research, Pune) and FAO
post-harvest storage guidelines for Allium cepa L.

Key Degradation Vectors Quantified:
1. Aspergillus niger (Black Mold) Fungal Load:
   - Primary vector of storage decay in Indian buffer stocks (Price Stabilisation Fund).
   - Exponential cross-contamination risk in stacked crates and cold storage pallets.
2. Papery Tunic Retention (Skin Baldness Index):
   - Intact dry outer scales provide critical barrier against desiccation and soft rot.
   - Baldness > 20% increases transpiration rate 4x, causing rapid weight loss.
3. Sprouting / Dormancy Breaking Risk:
   - End of dormancy leads to rapid internal moisture mobilization and core decay.
4. Morphological Sphericity & Size Vulnerability:
   - Oversized / jumbo bulbs (>65mm) and low sphericity bulbs feature thick, unsealed necks
     that serve as pathogen entry ports during storage.

Storage Categories:
- BUFFER_STOCK_PREMIUM: Safe for 90 to 120+ days in ventilated cold storage (0-2°C, 65-70% RH).
- STANDARD_COLD_STORAGE: Safe for 45 to 60 days in cold storage.
- RAPID_DISPATCH_AUCTION: High decay risk. Fast-track to retail markets within 7 to 14 days.
- UNFIT_FOR_STORAGE: Immediate cull / industrial processing; high rot contagion.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

logger = logging.getLogger(__name__)


@dataclass
class BulbStorageProfile:
    """Storageability assessment for an individual onion bulb."""
    bulb_index: int
    storageability_score: float      # 0.0 to 100.0 (higher is better)
    shelf_life_days_est: int         # Estimated survival days under standard storage
    storage_tier: str                # PREMIUM | STANDARD | RAPID_DISPATCH | CRITICAL
    decay_risk_factors: list[str]    # Specific biological risk flags


@dataclass
class LotStorageAdvisory:
    """Consignment-level cold storage preservation and dispatch advisory."""
    mean_storageability_score: float       # 0.0 to 100.0
    storage_recommendation: str            # BUFFER_STOCK_PREMIUM | STANDARD_COLD_STORAGE | RAPID_DISPATCH_AUCTION | UNFIT_FOR_STORAGE
    recommended_max_storage_days: int      # Maximum safe storage window in days
    respiration_risk_level: str            # LOW | MODERATE | HIGH | CRITICAL
    fungal_spore_exposure_pct: float       # Percentage of bulbs carrying Aspergillus niger spores
    tunic_loss_exposure_pct: float         # Percentage of bulbs with substantial tunic peel (>15%)
    dormancy_break_exposure_pct: float     # Percentage of bulbs showing sprout onset
    recommended_action: str                # Prescriptive operational recommendation for NAFED officer
    storage_suitability_breakdown: dict    # { "premium_pct": X, "standard_pct": Y, "dispatch_pct": Z, "cull_pct": W }

    def as_dict(self) -> dict:
        return {
            "mean_storageability_score": self.mean_storageability_score,
            "storage_recommendation": self.storage_recommendation,
            "recommended_max_storage_days": self.recommended_max_storage_days,
            "respiration_risk_level": self.respiration_risk_level,
            "fungal_spore_exposure_pct": self.fungal_spore_exposure_pct,
            "tunic_loss_exposure_pct": self.tunic_loss_exposure_pct,
            "dormancy_break_exposure_pct": self.dormancy_break_exposure_pct,
            "recommended_action": self.recommended_action,
            "storage_suitability_breakdown": self.storage_suitability_breakdown,
        }


def assess_bulb_storageability(
    bulb_index: int,
    diameter_mm: float | None,
    black_mold_pct: float,
    skin_baldness_pct: float,
    circularity: float,
    is_double_bulb: bool,
    rotten_prob: float,
    sprouted_prob: float,
    damaged_prob: float,
) -> BulbStorageProfile:
    """
    Compute storageability score (0-100) and shelf-life prediction for a single bulb.
    """
    score = 100.0
    risk_factors: list[str] = []

    # 1. Rot / Mold Penalties (Exponential impact on storageability)
    if rotten_prob >= 0.50:
        score -= 75.0
        risk_factors.append("Active Rot / Pathological Decay Detected")
    elif rotten_prob > 0.20:
        score -= (rotten_prob * 40.0)

    if black_mold_pct > 15.0:
        score -= 40.0
        risk_factors.append(f"Severe Aspergillus Niger Load ({black_mold_pct:.1f}% surface area)")
    elif black_mold_pct > 5.0:
        score -= (black_mold_pct * 1.8)
        risk_factors.append(f"Moderate Aspergillus Spores ({black_mold_pct:.1f}% surface area)")

    # 2. Sprouting / Dormancy Breaking
    if sprouted_prob >= 0.50:
        score -= 60.0
        risk_factors.append("Visible Sprout / Dormancy Broken")
    elif sprouted_prob > 0.20:
        score -= (sprouted_prob * 35.0)

    # 3. Papery Tunic / Skin Baldness (Desiccation and mechanical vulnerability)
    if skin_baldness_pct > 25.0:
        score -= 25.0
        risk_factors.append(f"Severe Skin Baldness ({skin_baldness_pct:.1f}% fleshy scale exposed)")
    elif skin_baldness_pct > 10.0:
        score -= (skin_baldness_pct * 0.8)

    # 4. Double / Split Bulbs & High Neck Ratio
    if is_double_bulb:
        score -= 30.0
        risk_factors.append("Double/Split Bulb (Open Neck Crevice)")

    if circularity < 0.70:
        score -= 10.0
        risk_factors.append("Poor Sphericity / Elongated Neck")

    # 5. Size Extreme Penalty
    if diameter_mm is not None:
        if diameter_mm > 68.0:
            score -= 15.0
            risk_factors.append(f"Jumbo Diameter ({diameter_mm:.1f}mm, high respiration rate)")
        elif diameter_mm < 35.0:
            score -= 10.0
            risk_factors.append(f"Goli Diameter ({diameter_mm:.1f}mm, prone to desiccation)")

    # 6. Mechanical Damage
    if damaged_prob >= 0.50:
        score -= 20.0
        risk_factors.append("Mechanical Cuts / Bruising")

    score = max(0.0, min(100.0, score))

    # Shelf-life projection based on score
    if score >= 85.0:
        shelf_life_days = int(90 + (score - 85.0) * 2.0)  # 90-120 days
        tier = "PREMIUM"
    elif score >= 65.0:
        shelf_life_days = int(45 + (score - 65.0) * 2.25) # 45-90 days
        tier = "STANDARD"
    elif score >= 40.0:
        shelf_life_days = int(14 + (score - 40.0) * 1.2)  # 14-45 days
        tier = "RAPID_DISPATCH"
    else:
        shelf_life_days = int(max(1, score * 0.35))       # 1-14 days
        tier = "CRITICAL"

    return BulbStorageProfile(
        bulb_index=bulb_index,
        storageability_score=round(score, 1),
        shelf_life_days_est=shelf_life_days,
        storage_tier=tier,
        decay_risk_factors=risk_factors,
    )


def compute_lot_storage_advisory(
    profiles: Sequence[BulbStorageProfile],
) -> LotStorageAdvisory:
    """
    Aggregate bulb-level storage assessments into a comprehensive consignment storage advisory.
    """
    if not profiles:
        return LotStorageAdvisory(
            mean_storageability_score=0.0,
            storage_recommendation="UNFIT_FOR_STORAGE",
            recommended_max_storage_days=0,
            respiration_risk_level="CRITICAL",
            fungal_spore_exposure_pct=0.0,
            tunic_loss_exposure_pct=0.0,
            dormancy_break_exposure_pct=0.0,
            recommended_action="No bulb profiles available to assess storageability.",
            storage_suitability_breakdown={"premium_pct": 0, "standard_pct": 0, "dispatch_pct": 0, "cull_pct": 0},
        )

    n = len(profiles)
    scores = [p.storageability_score for p in profiles]
    mean_score = sum(scores) / n

    premium_cnt = sum(1 for p in profiles if p.storage_tier == "PREMIUM")
    standard_cnt = sum(1 for p in profiles if p.storage_tier == "STANDARD")
    dispatch_cnt = sum(1 for p in profiles if p.storage_tier == "RAPID_DISPATCH")
    cull_cnt = sum(1 for p in profiles if p.storage_tier == "CRITICAL")

    # Pathological & physical defect exposures
    mold_cnt = sum(1 for p in profiles if any("Aspergillus" in r or "Rot" in r for r in p.decay_risk_factors))
    tunic_loss_cnt = sum(1 for p in profiles if any("Baldness" in r for r in p.decay_risk_factors))
    sprout_cnt = sum(1 for p in profiles if any("Sprout" in r for r in p.decay_risk_factors))

    mold_pct = round((mold_cnt / n) * 100.0, 1)
    tunic_pct = round((tunic_loss_cnt / n) * 100.0, 1)
    sprout_pct = round((sprout_cnt / n) * 100.0, 1)

    breakdown = {
        "premium_pct": round((premium_cnt / n) * 100.0, 1),
        "standard_pct": round((standard_cnt / n) * 100.0, 1),
        "dispatch_pct": round((dispatch_cnt / n) * 100.0, 1),
        "cull_pct": round((cull_cnt / n) * 100.0, 1),
    }

    # Prescriptive logic grounded in NAFED procurement protocol
    if mold_pct > 15.0 or cull_cnt / n > 0.20 or mean_score < 45.0:
        recommendation = "UNFIT_FOR_STORAGE"
        max_days = 7
        risk = "CRITICAL"
        action = (
            "REJECT BUFFER STOCK: High contagion risk. Aspergillus fungal spores and soft decay "
            "exceed safe containment limits. Stack collapse and pallet rot will occur if stored. "
            "Divert to local open market or industrial dehydrated onion processing immediately."
        )
    elif sprout_pct > 8.0 or mold_pct > 6.0 or mean_score < 65.0:
        recommendation = "RAPID_DISPATCH_AUCTION"
        max_days = 21
        risk = "HIGH"
        action = (
            "FAST-TRACK DISPATCH: Dormancy breakdown or fungal pressure detected. "
            "Unsuitable for long-term buffer stock. Fast-track allocation to retail consumer centers "
            "(e.g., Mother Dairy / Safal / NCCF mobile vans) within 14-21 days."
        )
    elif mean_score >= 80.0 and (premium_cnt + standard_cnt) / n >= 0.85:
        recommendation = "BUFFER_STOCK_PREMIUM"
        max_days = 120
        risk = "LOW"
        action = (
            "APPROVED FOR NAFED BUFFER STOCK: Exceptional curing quality, tight neck closure, "
            "and robust protective outer scales. Approved for long-term ventilated cold storage "
            "(0–2°C, 65–70% RH) for up to 120 days."
        )
    else:
        recommendation = "STANDARD_COLD_STORAGE"
        max_days = 60
        risk = "MODERATE"
        action = (
            "QUALIFIED FOR INTERMEDIATE BUFFER STOCK: Standard quality with minor variance. "
            "Store in monitored cold chambers for up to 60 days. Periodic gas/RH sensor checks recommended."
        )

    return LotStorageAdvisory(
        mean_storageability_score=round(mean_score, 1),
        storage_recommendation=recommendation,
        recommended_max_storage_days=max_days,
        respiration_risk_level=risk,
        fungal_spore_exposure_pct=mold_pct,
        tunic_loss_exposure_pct=tunic_pct,
        dormancy_break_exposure_pct=sprout_pct,
        recommended_action=action,
        storage_suitability_breakdown=breakdown,
    )
