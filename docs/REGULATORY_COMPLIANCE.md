# CEPA Regulatory Compliance & Standards Alignment Matrix

> **Authoritative References**:  
> - Bureau of Indian Standards: **BIS IS 17912:2022** (*Onion Bulbs — Specification and Grading*)  
> - Department of Consumer Affairs / NAFED: **Price Stabilisation Fund (PSF) FAQ Guidelines**  
> - Ministry of Agriculture & Farmers Welfare: **eNAM Assaying Schema v2.1 (XML)**  
> - Directorate of Marketing and Inspection (DMI): **Agmark Grading & Marking Rules**

---

## 1. BIS IS 17912:2022 Size Classification Mapping

BIS IS 17912:2022 specifies five standardized size classifications for mature dry onions (*Allium cepa* L.) based on maximum equatorial diameter:

| BIS Size Grade | Equatorial Caliper Range ($d_{\text{eq}}$) | CEPA Metrology Classification | NAFED Buffer Stock Eligibility |
| :--- | :--- | :--- | :--- |
| **Extra Large** | $> 70.0\text{ mm}$ | `EXTRA_LARGE` | Premium Commercial |
| **Large** | $55.0\text{ mm} \le d < 70.0\text{ mm}$ | `LARGE` | Prime Buffer Stock (Grade A) |
| **Medium** | $45.0\text{ mm} \le d < 55.0\text{ mm}$ | `MEDIUM` | Standard Buffer Stock (Grade A) |
| **Small** | $35.0\text{ mm} \le d < 45.0\text{ mm}$ | `SMALL` | Under-Regulated Standard (URS) |
| **Very Small (Goli)** | $< 35.0\text{ mm}$ | `VERY_SMALL` | Dockage Penalty / Reject |

### Permissible Size Tolerances (Clause 5.3)
- For lots declared as a specific size class (e.g. Medium 45–55 mm), BIS allows a maximum of **5.0% by weight** of bulbs below the minimum size and **10.0% by weight** above the maximum size.
- CEPA automatically compiles size tolerance compliance histograms and flags out-of-tolerance consignments on the official settlement certificate.

---

## 2. NAFED Price Stabilisation Fund (PSF) FAQ Quality Parameters

Under government market intervention operations for onion buffer creation (e.g. 5.0 Lakh Metric Tonnes target), NAFED enforces Fair Average Quality (FAQ) parameters. CEPA codifies these dockage rules:

| Quality Parameter | NAFED FAQ Permissible Limit | Penalty / Dockage Schedule | CEPA Automated Valuation Logic |
| :--- | :--- | :--- | :--- |
| **Under-Size Bulbs (< 40 mm)** | Max 5.0% by weight | Above 5%: Pro-rata deduction of ₹15/qtl per 1% excess | `commercial_settlement.py::calc_size_dockage()` |
| **Damaged / Deformed / Split** | Max 3.0% by weight | Above 3%: Pro-rata deduction of ₹25/qtl per 1% excess | `commercial_settlement.py::calc_damage_dockage()` |
| **Sprouted Bulbs** | Max 1.0% by weight | Above 1%: Pro-rata deduction of ₹40/qtl per 1% excess; > 5% causes lot rejection | `commercial_settlement.py::calc_sprout_dockage()` |
| **Rotten / Soft / Black Mold** | Max 1.5% by weight | Above 1.5%: Pro-rata deduction of ₹60/qtl per 1% excess; > 4% causes outright lot rejection | `commercial_settlement.py::calc_rot_dockage()` |
| **Moisture / Surface Wetness** | Max 12.0% | Wet lots rejected or assessed mandatory 2.5% weight tare | Flagged via CIE-LAB high-specularity tunic reflection |

---

## 3. eNAM XML Schema v2.1 Verification & Export Matrix

CEPA provides full export compliance for the National Agriculture Market (eNAM) automated assaying interface (`GET /api/v1/inspections/{id}/enam?format=xml`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<eNAMQualityAssayingReport version="2.1" xmlns="http://enam.gov.in/schema/assaying/v2.1">
  <Header>
    <MandiCode>MH-NSK-001</MandiCode>
    <LotID>LOT-2026-9812</LotID>
    <CommodityCode>COMM-ONION-RABI</CommodityCode>
    <AssayingTimestamp>2026-10-04T16:15:00Z</AssayingTimestamp>
    <AssayingMethod>AUTONOMOUS_COMPUTER_VISION_CHARUCO</AssayingMethod>
  </Header>
  <QualityParameters>
    <Parameter code="EQUATORIAL_MEAN_MM" uom="mm">54.2</Parameter>
    <Parameter code="GRADE_A_PERCENT" uom="%">78.5</Parameter>
    <Parameter code="URS_PERCENT" uom="%">14.5</Parameter>
    <Parameter code="REJECTED_PERCENT" uom="%">7.0</Parameter>
    <Parameter code="ROTTEN_PERCENT" uom="%">0.8</Parameter>
    <Parameter code="SPROUTED_PERCENT" uom="%">1.2</Parameter>
    <Parameter code="STORAGEABILITY_SCORE" uom="index">87.5</Parameter>
  </QualityParameters>
  <SovereignCryptographicSeal>
    <Algorithm>HMAC-SHA256</Algorithm>
    <SealSignature>a7c1b5204ef83921...64hexChars</SealSignature>
    <RawImageDigestSHA256>3b91a78028ef71...64hexChars</RawImageDigestSHA256>
    <VerificationStatus>VALID_SEALED</VerificationStatus>
  </SovereignCryptographicSeal>
</eNAMQualityAssayingReport>
```

Field validation rules:
- `MandiCode`: Matches registered APMC mandi identifiers.
- `AssayingTimestamp`: ISO 8601 UTC string.
- `SealSignature`: Full 64-character HMAC-SHA256 hex string validating certificate non-repudiation.
