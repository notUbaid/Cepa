"""
Cepa Mandi Commercial Settlement & NAFED FAQ Dockage Engine.

Formalizes the economic transaction between agricultural producers (farmers)
and procurement agencies (NAFED / NCCF / APMC Traders).

Regulatory Standards Applied:
- NAFED Price Stabilisation Fund (PSF) Operational Guidelines for Onion Procurement
- BIS IS 17912:2022 (Supply Chain of Onions — Sizing and Grading Requirements)
- Department of Consumer Affairs (DCA) Quality Assurance Protocols

Settlement Formula:
  Net Rate (₹/qtl) = Base MSP - (Size Dockage + Defect Dockage + Storageability Discount)
  Total Lot Payout (₹) = Net Rate (₹/qtl) × Net Lot Weight (qtls)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Standard NAFED Rabi/Kharif procurement benchmark (INR per quintal = 100 kg)
DEFAULT_BASE_MSP_INR_PER_QTL = 2410.0


@dataclass
class DockageItem:
    """Individual itemized penalty or deduction."""
    category: str              # SIZE_VARIANCE | DEFECT_VARIANCE | MOISTURE_TUNIC
    title: str                 # Human-readable title
    measured_pct: float        # Observed percentage
    permissible_limit_pct: float # Free FAQ tolerance threshold
    excess_pct: float          # Variance above permissible limit
    deduction_inr_per_qtl: float # Deduction in ₹/quintal
    reason: str                # Agronomic justification


@dataclass
class MandiSettlementSlip:
    """Comprehensive commercial payment voucher and dockage breakdown."""
    base_msp_inr_per_qtl: float
    net_payout_rate_inr_per_qtl: float
    total_dockage_inr_per_qtl: float
    dockage_items: list[DockageItem]
    settlement_tier: str              # FULL_MSP_PAYOUT | PROPORTIONAL_DOCKAGE | REJECTED_NO_PAYOUT
    procurement_decision: str         # APPROVED_FOR_PROCUREMENT | CONDITIONAL_ACCEPTANCE | CONSIGNMENT_REJECTED
    assumed_lot_weight_quintals: float # Default 50 qtl (5 MT)
    estimated_gross_payout_inr: float
    estimated_net_payout_inr: float
    commercial_remarks: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_msp_inr_per_qtl": self.base_msp_inr_per_qtl,
            "net_payout_rate_inr_per_qtl": self.net_payout_rate_inr_per_qtl,
            "total_dockage_inr_per_qtl": self.total_dockage_inr_per_qtl,
            "dockage_items": [
                {
                    "category": item.category,
                    "title": item.title,
                    "measured_pct": item.measured_pct,
                    "permissible_limit_pct": item.permissible_limit_pct,
                    "excess_pct": item.excess_pct,
                    "deduction_inr_per_qtl": item.deduction_inr_per_qtl,
                    "reason": item.reason,
                }
                for item in self.dockage_items
            ],
            "settlement_tier": self.settlement_tier,
            "procurement_decision": self.procurement_decision,
            "assumed_lot_weight_quintals": self.assumed_lot_weight_quintals,
            "estimated_gross_payout_inr": self.estimated_gross_payout_inr,
            "estimated_net_payout_inr": self.estimated_net_payout_inr,
            "commercial_remarks": self.commercial_remarks,
        }


def calculate_mandi_settlement(
    total_bulbs: int,
    grade_a_count: int,
    urs_count: int,
    rejected_count: int,
    rotten_count: int,
    sprouted_count: int,
    undersized_count: int,
    oversized_count: int,
    storageability_score: float = 85.0,
    base_msp_inr_per_qtl: float = DEFAULT_BASE_MSP_INR_PER_QTL,
    consignment_weight_qtls: float = 50.0,
) -> MandiSettlementSlip:
    """
    Compute official NAFED FAQ mandi settlement slip with itemized dockage deductions.
    """
    if total_bulbs <= 0:
        return MandiSettlementSlip(
            base_msp_inr_per_qtl=base_msp_inr_per_qtl,
            net_payout_rate_inr_per_qtl=0.0,
            total_dockage_inr_per_qtl=base_msp_inr_per_qtl,
            dockage_items=[],
            settlement_tier="REJECTED_NO_PAYOUT",
            procurement_decision="CONSIGNMENT_REJECTED",
            assumed_lot_weight_quintals=consignment_weight_qtls,
            estimated_gross_payout_inr=0.0,
            estimated_net_payout_inr=0.0,
            commercial_remarks="No bulb observations recorded.",
        )

    # 1. Defect percentages
    rot_pct = (rotten_count / total_bulbs) * 100.0
    sprout_pct = (sprouted_count / total_bulbs) * 100.0
    undersize_pct = (undersized_count / total_bulbs) * 100.0
    oversize_pct = (oversized_count / total_bulbs) * 100.0
    reject_pct = (rejected_count / total_bulbs) * 100.0

    # 2. Hard Rejection Check
    # NAFED PSF Rule: Rot > 5.0% or Total Rejection > 25.0% renders lot unprocureable
    if rot_pct > 5.0 or sprout_pct > 6.0 or reject_pct > 25.0:
        return MandiSettlementSlip(
            base_msp_inr_per_qtl=base_msp_inr_per_qtl,
            net_payout_rate_inr_per_qtl=0.0,
            total_dockage_inr_per_qtl=base_msp_inr_per_qtl,
            dockage_items=[
                DockageItem(
                    category="DEFECT_VARIANCE",
                    title="Critical Pathological Rot / Sprout Limit Exceeded",
                    measured_pct=round(rot_pct + sprout_pct, 1),
                    permissible_limit_pct=5.0,
                    excess_pct=round(max(0.0, (rot_pct + sprout_pct) - 5.0), 1),
                    deduction_inr_per_qtl=base_msp_inr_per_qtl,
                    reason="Consignment exceeds maximum allowable disease/rot limits. Rejected without payment under PSF FAQ guidelines.",
                )
            ],
            settlement_tier="REJECTED_NO_PAYOUT",
            procurement_decision="CONSIGNMENT_REJECTED",
            assumed_lot_weight_quintals=consignment_weight_qtls,
            estimated_gross_payout_inr=round(base_msp_inr_per_qtl * consignment_weight_qtls, 2),
            estimated_net_payout_inr=0.0,
            commercial_remarks="Consignment disqualified from procurement. Exceeds critical biological decay threshold.",
        )

    dockage_items: list[DockageItem] = []
    total_deductions_inr = 0.0

    # 3. Itemized Size Dockage
    # Under-sized (<45mm / Goli): Permissible FAQ tolerance is 5.0%
    if undersize_pct > 5.0:
        excess_undersize = undersize_pct - 5.0
        # ₹15 per quintal per 1% excess undersize
        deduction = round(excess_undersize * 15.0, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="SIZE_VARIANCE",
            title="Undersized Bulbs (<45 mm Goli)",
            measured_pct=round(undersize_pct, 1),
            permissible_limit_pct=5.0,
            excess_pct=round(excess_undersize, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Excess small bulbs beyond 5% tolerance docked @ ₹15/qtl per percent.",
        ))

    # Over-sized (>65mm / Jumbo): Permissible FAQ tolerance is 5.0%
    if oversize_pct > 5.0:
        excess_oversize = oversize_pct - 5.0
        deduction = round(excess_oversize * 10.0, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="SIZE_VARIANCE",
            title="Oversized Bulbs (>65 mm Jumbo)",
            measured_pct=round(oversize_pct, 1),
            permissible_limit_pct=5.0,
            excess_pct=round(excess_oversize, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Excess thick-neck bulbs docked @ ₹10/qtl per percent.",
        ))

    # 4. Itemized Defect Dockage
    # Minor rot (2% - 5%): ₹40 per quintal per 1% excess
    if rot_pct > 2.0:
        excess_rot = rot_pct - 2.0
        deduction = round(excess_rot * 40.0, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="DEFECT_VARIANCE",
            title="Pathological Decay / Black Mold",
            measured_pct=round(rot_pct, 1),
            permissible_limit_pct=2.0,
            excess_pct=round(excess_rot, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Decay beyond 2% FAQ tolerance docked @ ₹40/qtl per percent.",
        ))

    # Minor sprouting (2% - 6%): ₹30 per quintal per 1% excess
    if sprout_pct > 2.0:
        excess_sprout = sprout_pct - 2.0
        deduction = round(excess_sprout * 30.0, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="DEFECT_VARIANCE",
            title="Sprouted / Bolted Bulbs",
            measured_pct=round(sprout_pct, 1),
            permissible_limit_pct=2.0,
            excess_pct=round(excess_sprout, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Sprouting beyond 2% FAQ tolerance docked @ ₹30/qtl per percent.",
        ))

    # 5. Storageability Quality Adjustment
    # If storageability score is below 65, apply ₹50/qtl handling/sorting surcharge
    if storageability_score < 65.0:
        surcharge = 50.0
        total_deductions_inr += surcharge
        dockage_items.append(DockageItem(
            category="STORAGE_RISK",
            title="Cold Storage Decay Surcharge",
            measured_pct=round(storageability_score, 1),
            permissible_limit_pct=65.0,
            excess_pct=round(65.0 - storageability_score, 1),
            deduction_inr_per_qtl=surcharge,
            reason="Sub-standard shelf-life score requires rapid dispatch handling.",
        ))

    # Cap dockage at 40% of Base MSP to prevent negative or unfair exploitation
    total_deductions_inr = min(total_deductions_inr, base_msp_inr_per_qtl * 0.40)
    net_payout_rate = round(base_msp_inr_per_qtl - total_deductions_inr, 2)

    tier = "FULL_MSP_PAYOUT" if total_deductions_inr == 0.0 else "PROPORTIONAL_DOCKAGE"
    decision = "APPROVED_FOR_PROCUREMENT" if total_deductions_inr == 0.0 else "CONDITIONAL_ACCEPTANCE"
    remarks = (
        "Meets full NAFED Fair Average Quality (FAQ) Grade A standard. 100% MSP payout approved."
        if total_deductions_inr == 0.0
        else f"Standard NAFED dockage deduction of ₹{total_deductions_inr:.1f}/qtl applied for off-grade variances."
    )

    gross_payout = round(base_msp_inr_per_qtl * consignment_weight_qtls, 2)
    net_payout = round(net_payout_rate * consignment_weight_qtls, 2)

    return MandiSettlementSlip(
        base_msp_inr_per_qtl=base_msp_inr_per_qtl,
        net_payout_rate_inr_per_qtl=net_payout_rate,
        total_dockage_inr_per_qtl=round(total_deductions_inr, 2),
        dockage_items=dockage_items,
        settlement_tier=tier,
        procurement_decision=decision,
        assumed_lot_weight_quintals=consignment_weight_qtls,
        estimated_gross_payout_inr=gross_payout,
        estimated_net_payout_inr=net_payout,
        commercial_remarks=remarks,
    )
