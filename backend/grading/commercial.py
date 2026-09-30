"""
Cepa Mandi Commercial Settlement & NAFED FAQ Dockage Engine.

Formalizes the economic appraisal and dockage simulation between agricultural
producers (farmers) and procurement agencies (NAFED / NCCF / APMC Traders).

Regulatory Standards and Policy Context:
- Onion is not covered under statutory Minimum Support Price (MSP) by CACP.
  Procurement by NAFED / NCCF operates under the Price Stabilisation Fund (PSF)
  or Market Intervention Scheme (MIS) using market-linked benchmark procurement
  rates established on a tender-by-tender basis.
- BIS IS 17912:2022 (Supply Chain of Onions -- Sizing and Grading Requirements)
- Department of Consumer Affairs (DCA) Quality Assurance Protocols for Buffer Stock

Settlement Formula:
  Net Rate (INR/qtl) = Benchmark Rate - (Size Dockage + Defect Dockage + Storageability Discount)
  Total Lot Payout (INR) = Net Rate (INR/qtl) * Net Lot Weight (qtls)

All rupee payouts and dockage calculations in this module represent illustrative
tender simulations based on configurable dockage parameters.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Standard NAFED Rabi/Kharif benchmark reference rate (INR per quintal = 100 kg)
# Configurable per mandi tender auction
DEFAULT_BENCHMARK_RATE_INR_PER_QTL = 2410.0
DEFAULT_BASE_MSP_INR_PER_QTL = DEFAULT_BENCHMARK_RATE_INR_PER_QTL  # Backwards compatibility alias


@dataclass
class TenderParameters:
    """
    Configurable procurement tender parameters and dockage deduction schedule.
    Allows mandi officers to adjust rates to match the active procurement tender.
    """
    benchmark_rate_inr_per_qtl: float = 2410.0
    undersize_dockage_per_pct: float = 15.0      # INR/qtl docked per 1% excess undersize (<45mm)
    oversize_dockage_per_pct: float = 10.0       # INR/qtl docked per 1% excess oversize (>65mm)
    rot_dockage_per_pct: float = 40.0            # INR/qtl docked per 1% excess rot (2% to 5%)
    sprout_dockage_per_pct: float = 30.0         # INR/qtl docked per 1% excess sprout (2% to 6%)
    storage_surcharge_inr_per_qtl: float = 50.0  # INR/qtl surcharge if storageability < threshold
    storage_surcharge_threshold_score: float = 65.0
    max_dockage_pct_of_benchmark: float = 0.40   # Maximum dockage cap (e.g., 40% of benchmark)
    free_undersize_tolerance_pct: float = 5.0    # Permissible FAQ tolerance before dockage
    free_oversize_tolerance_pct: float = 5.0     # Permissible FAQ tolerance before dockage
    free_rot_tolerance_pct: float = 2.0          # Permissible FAQ tolerance before dockage
    free_sprout_tolerance_pct: float = 2.0       # Permissible FAQ tolerance before dockage
    rot_rejection_limit_pct: float = 5.0         # Hard rejection if rot exceeds this
    sprout_rejection_limit_pct: float = 6.0      # Hard rejection if sprouting exceeds this
    total_rejection_limit_pct: float = 25.0      # Hard rejection if total rejects exceed this


@dataclass
class DockageItem:
    """Individual itemized penalty or deduction."""
    category: str              # SIZE_VARIANCE | DEFECT_VARIANCE | STORAGE_RISK
    title: str                 # Human-readable title
    measured_pct: float        # Observed percentage
    permissible_limit_pct: float # Free FAQ tolerance threshold
    excess_pct: float          # Variance above permissible limit
    deduction_inr_per_qtl: float # Deduction in INR/quintal
    reason: str                # Agronomic and tender justification


@dataclass
class MandiSettlementSlip:
    """Comprehensive commercial payment voucher and dockage breakdown."""
    base_msp_inr_per_qtl: float                  # Benchmark procurement rate (INR/qtl)
    net_payout_rate_inr_per_qtl: float           # Net payable rate after itemized dockage
    total_dockage_inr_per_qtl: float             # Sum of dockage deductions (INR/qtl)
    dockage_items: list[DockageItem]             # Itemized deductions
    settlement_tier: str                         # FULL_MSP_PAYOUT | PROPORTIONAL_DOCKAGE | REJECTED_NO_PAYOUT
    procurement_decision: str                    # APPROVED_FOR_PROCUREMENT | CONDITIONAL_ACCEPTANCE | CONSIGNMENT_REJECTED
    assumed_lot_weight_quintals: float           # Reference lot weight (default 50 qtls = 5 MT)
    estimated_gross_payout_inr: float            # Gross value at base benchmark rate
    estimated_net_payout_inr: float              # Net payable lot value
    commercial_remarks: str                      # Regulatory and dockage remarks
    benchmark_rate_inr_per_qtl: float = 2410.0   # Explicit tender benchmark rate
    is_illustrative: bool = True                 # Flags simulation vs official tender contract
    disclaimer: str = (
        "Illustrative tender simulation. Onion has no statutory MSP; procurement operates under "
        "the Price Stabilisation Fund (PSF) at market-linked benchmark rates set by procurement tenders."
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "base_msp_inr_per_qtl": self.base_msp_inr_per_qtl,
            "benchmark_rate_inr_per_qtl": self.benchmark_rate_inr_per_qtl,
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
            "is_illustrative": self.is_illustrative,
            "disclaimer": self.disclaimer,
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
    base_msp_inr_per_qtl: float | None = None,
    benchmark_rate_inr_per_qtl: float | None = None,
    consignment_weight_qtls: float = 50.0,
    tender_params: TenderParameters | None = None,
) -> MandiSettlementSlip:
    """
    Compute illustrative NAFED / APMC mandi settlement slip with itemized FAQ dockage.

    Onion has no statutory MSP; rates and dockage deductions are determined by
    active procurement tender parameters under the Price Stabilisation Fund (PSF).
    """
    if tender_params is None:
        tender_params = TenderParameters()

    # Determine base rate: explicit argument overrides default tender benchmark
    effective_rate = (
        benchmark_rate_inr_per_qtl
        if benchmark_rate_inr_per_qtl is not None
        else (base_msp_inr_per_qtl if base_msp_inr_per_qtl is not None else tender_params.benchmark_rate_inr_per_qtl)
    )

    if total_bulbs <= 0:
        return MandiSettlementSlip(
            base_msp_inr_per_qtl=effective_rate,
            benchmark_rate_inr_per_qtl=effective_rate,
            net_payout_rate_inr_per_qtl=0.0,
            total_dockage_inr_per_qtl=effective_rate,
            dockage_items=[],
            settlement_tier="REJECTED_NO_PAYOUT",
            procurement_decision="CONSIGNMENT_REJECTED",
            assumed_lot_weight_quintals=consignment_weight_qtls,
            estimated_gross_payout_inr=0.0,
            estimated_net_payout_inr=0.0,
            commercial_remarks="No bulb observations recorded. Settlement cannot be computed.",
        )

    # 1. Defect percentages
    rot_pct = (rotten_count / total_bulbs) * 100.0
    sprout_pct = (sprouted_count / total_bulbs) * 100.0
    undersize_pct = (undersized_count / total_bulbs) * 100.0
    oversize_pct = (oversized_count / total_bulbs) * 100.0
    reject_pct = (rejected_count / total_bulbs) * 100.0

    # 2. Hard Rejection Check
    # NAFED PSF Rule: Rot > 5.0%, Sprout > 6.0%, or Total Rejection > 25.0% renders lot unprocureable
    if (
        rot_pct > tender_params.rot_rejection_limit_pct
        or sprout_pct > tender_params.sprout_rejection_limit_pct
        or reject_pct > tender_params.total_rejection_limit_pct
    ):
        return MandiSettlementSlip(
            base_msp_inr_per_qtl=effective_rate,
            benchmark_rate_inr_per_qtl=effective_rate,
            net_payout_rate_inr_per_qtl=0.0,
            total_dockage_inr_per_qtl=effective_rate,
            dockage_items=[
                DockageItem(
                    category="DEFECT_VARIANCE",
                    title="Critical Pathological Rot / Sprout Limit Exceeded",
                    measured_pct=round(rot_pct + sprout_pct, 1),
                    permissible_limit_pct=tender_params.free_rot_tolerance_pct + tender_params.free_sprout_tolerance_pct,
                    excess_pct=round(max(0.0, (rot_pct + sprout_pct) - (tender_params.free_rot_tolerance_pct + tender_params.free_sprout_tolerance_pct)), 1),
                    deduction_inr_per_qtl=effective_rate,
                    reason=(
                        "Consignment exceeds maximum allowable disease/rot limits. Rejected without payment "
                        "under Price Stabilisation Fund (PSF) Fair Average Quality (FAQ) guidelines."
                    ),
                )
            ],
            settlement_tier="REJECTED_NO_PAYOUT",
            procurement_decision="CONSIGNMENT_REJECTED",
            assumed_lot_weight_quintals=consignment_weight_qtls,
            estimated_gross_payout_inr=round(effective_rate * consignment_weight_qtls, 2),
            estimated_net_payout_inr=0.0,
            commercial_remarks=(
                "Consignment disqualified from procurement. Exceeds critical biological decay threshold "
                f"(observed rot: {rot_pct:.1f}%, sprout: {sprout_pct:.1f}%)."
            ),
        )

    dockage_items: list[DockageItem] = []
    total_deductions_inr = 0.0

    # 3. Itemized Size Dockage
    # Under-sized (<45mm / Goli): Permissible FAQ tolerance is typically 5.0%
    if undersize_pct > tender_params.free_undersize_tolerance_pct:
        excess_undersize = undersize_pct - tender_params.free_undersize_tolerance_pct
        deduction = round(excess_undersize * tender_params.undersize_dockage_per_pct, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="SIZE_VARIANCE",
            title="Undersized Bulbs (<45 mm Goli)",
            measured_pct=round(undersize_pct, 1),
            permissible_limit_pct=tender_params.free_undersize_tolerance_pct,
            excess_pct=round(excess_undersize, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Excess small bulbs beyond {tender_params.free_undersize_tolerance_pct}% tolerance docked @ INR {tender_params.undersize_dockage_per_pct}/qtl per percent.",
        ))

    # Over-sized (>65mm / Jumbo): Permissible FAQ tolerance is typically 5.0%
    if oversize_pct > tender_params.free_oversize_tolerance_pct:
        excess_oversize = oversize_pct - tender_params.free_oversize_tolerance_pct
        deduction = round(excess_oversize * tender_params.oversize_dockage_per_pct, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="SIZE_VARIANCE",
            title="Oversized Bulbs (>65 mm Jumbo)",
            measured_pct=round(oversize_pct, 1),
            permissible_limit_pct=tender_params.free_oversize_tolerance_pct,
            excess_pct=round(excess_oversize, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Excess thick-neck bulbs beyond {tender_params.free_oversize_tolerance_pct}% tolerance docked @ INR {tender_params.oversize_dockage_per_pct}/qtl per percent.",
        ))

    # 4. Itemized Defect Dockage
    # Minor rot (2% - 5%): docked per percent excess
    if rot_pct > tender_params.free_rot_tolerance_pct:
        excess_rot = rot_pct - tender_params.free_rot_tolerance_pct
        deduction = round(excess_rot * tender_params.rot_dockage_per_pct, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="DEFECT_VARIANCE",
            title="Pathological Decay / Black Mold",
            measured_pct=round(rot_pct, 1),
            permissible_limit_pct=tender_params.free_rot_tolerance_pct,
            excess_pct=round(excess_rot, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Decay beyond {tender_params.free_rot_tolerance_pct}% FAQ tolerance docked @ INR {tender_params.rot_dockage_per_pct}/qtl per percent.",
        ))

    # Minor sprouting (2% - 6%): docked per percent excess
    if sprout_pct > tender_params.free_sprout_tolerance_pct:
        excess_sprout = sprout_pct - tender_params.free_sprout_tolerance_pct
        deduction = round(excess_sprout * tender_params.sprout_dockage_per_pct, 1)
        total_deductions_inr += deduction
        dockage_items.append(DockageItem(
            category="DEFECT_VARIANCE",
            title="Sprouted / Bolted Bulbs",
            measured_pct=round(sprout_pct, 1),
            permissible_limit_pct=tender_params.free_sprout_tolerance_pct,
            excess_pct=round(excess_sprout, 1),
            deduction_inr_per_qtl=deduction,
            reason=f"Sprouting beyond {tender_params.free_sprout_tolerance_pct}% FAQ tolerance docked @ INR {tender_params.sprout_dockage_per_pct}/qtl per percent.",
        ))

    # 5. Storageability Quality Adjustment
    # If storageability score is below threshold, apply handling/sorting surcharge
    if storageability_score < tender_params.storage_surcharge_threshold_score:
        surcharge = tender_params.storage_surcharge_inr_per_qtl
        total_deductions_inr += surcharge
        dockage_items.append(DockageItem(
            category="STORAGE_RISK",
            title="Cold Storage Decay Surcharge",
            measured_pct=round(storageability_score, 1),
            permissible_limit_pct=tender_params.storage_surcharge_threshold_score,
            excess_pct=round(tender_params.storage_surcharge_threshold_score - storageability_score, 1),
            deduction_inr_per_qtl=surcharge,
            reason="Sub-standard shelf-life score requires rapid dispatch and priority handling.",
        ))

    # Cap dockage at maximum allowable percentage of benchmark rate
    max_dockage = effective_rate * tender_params.max_dockage_pct_of_benchmark
    total_deductions_inr = min(total_deductions_inr, max_dockage)
    net_payout_rate = round(effective_rate - total_deductions_inr, 2)

    tier = "FULL_MSP_PAYOUT" if total_deductions_inr == 0.0 else "PROPORTIONAL_DOCKAGE"
    decision = "APPROVED_FOR_PROCUREMENT" if total_deductions_inr == 0.0 else "CONDITIONAL_ACCEPTANCE"
    remarks = (
        "Meets full NAFED Fair Average Quality (FAQ) Grade A standard. 100% benchmark procurement rate approved (illustrative)."
        if total_deductions_inr == 0.0
        else f"Standard NAFED dockage deduction of INR {total_deductions_inr:.1f}/qtl applied for off-grade variances (illustrative)."
    )

    gross_payout = round(effective_rate * consignment_weight_qtls, 2)
    net_payout = round(net_payout_rate * consignment_weight_qtls, 2)

    return MandiSettlementSlip(
        base_msp_inr_per_qtl=effective_rate,
        benchmark_rate_inr_per_qtl=effective_rate,
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
