import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { ApiClient } from '../api/client';
import { getApiBaseUrl, resolveMediaUrl } from '../config';
import { InspectionDetail, ReportDetail } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  GradeBadge,
  Haptics,
  Radius,
  Shadows,
  SkeletonBox,
  Spacing,
  Typography,
} from '../ui';

interface FinalReportScreenProps {
  inspection: InspectionDetail;
  onStartNewInspection: () => void;
}

export const FinalReportScreen: React.FC<FinalReportScreenProps> = ({
  inspection,
  onStartNewInspection,
}) => {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrCreateReport = async () => {
    try {
      setLoading(true);
      setError(null);
      let rep: ReportDetail;
      try {
        rep = await ApiClient.getReport(inspection.id);
      } catch {
        rep = await ApiClient.generateReport(inspection.id);
      }
      setReport(rep);
      Haptics.success();
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve or compile official certificate.');
      Haptics.error();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrCreateReport();
  }, [inspection.id]);

  const handleDownloadPdf = () => {
    Haptics.heavy();
    const pdfUrl = `${getApiBaseUrl()}/api/v1/inspections/${inspection.id}/reports/pdf`;
    Linking.openURL(pdfUrl).catch((e: any) => {
      Haptics.error();
      alert(`Could not open PDF: ${e.message}`);
    });
  };

  const handleOpenShareLink = () => {
    if (report?.share_url) {
      Haptics.light();
      const resolved = resolveMediaUrl(report.share_url) || report.share_url;
      Linking.openURL(resolved).catch((e: any) =>
        alert(`Could not open link: ${e.message}`)
      );
    }
  };

  const handleVerifySealOnline = () => {
    Haptics.medium();
    const url = report?.verify_url
      ? (resolveMediaUrl(report.verify_url) || report.verify_url)
      : `${getApiBaseUrl()}/api/v1/reports/${inspection.id}/verify?format=html`;
    Linking.openURL(url).catch((e: any) =>
      alert(`Could not open verification audit page: ${e.message}`)
    );
  };

  const [announcing, setAnnouncing] = useState(false);

  const handleBhashiniAnnounce = async (lang = 'hi') => {
    Haptics.medium();
    setAnnouncing(true);
    try {
      const res = await ApiClient.getMandiAnnouncement(inspection.id, lang);
      alert(
        `Bhashini Mandi Announcement (${res.language.toUpperCase()}):\n\n"${res.announcement_text}"\n\nRecommendation: ${res.lot_recommendation}`
      );
    } catch (e: any) {
      alert(`Announcement error: ${e.message}`);
    } finally {
      setAnnouncing(false);
    }
  };

  const handleExportEnam = () => {
    Haptics.light();
    const enamUrl = `${getApiBaseUrl()}/api/v1/inspections/${inspection.id}/enam?format=xml`;
    Linking.openURL(enamUrl).catch((e: any) => alert(`Could not open eNAM export: ${e.message}`));
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={Colors.accent} />
        <Text style={styles.loadingText}>Compiling official PDF certificate...</Text>
        <Text style={styles.loadingSub}>
          Calculating NAFED FAQ dockage deductions & BIS IS 17912:2022 size compliance...
        </Text>
      </View>
    );
  }

  if (error || !report) {
    return (
      <View style={styles.centerContainer}>
        <View style={styles.failGlowBadge}>
          <Feather name="alert-triangle" size={32} color="#dc2626" />
        </View>
        <Text style={styles.errorTitle}>Report Generation Failed</Text>
        <View style={styles.errorBtnRow}>
          <AnimatedPressable
            haptic="heavy"
            style={styles.retryBtnPrimary}
            onPress={fetchOrCreateReport}
          >
            <Text style={styles.retryBtnPrimaryText}>Retry Compilation</Text>
          </AnimatedPressable>
          <AnimatedPressable
            haptic="medium"
            style={styles.retryBtn}
            onPress={onStartNewInspection}
          >
            <Text style={styles.retryBtnText}>Return to Home</Text>
          </AnimatedPressable>
        </View>
      </View>
    );
  }

  // Commercial Settlement Data
  const commercial = report.commercial_settlement || {};
  const baseMsp = commercial.base_msp_inr_per_qtl ?? 2410.0;
  const netRate = commercial.net_payout_rate_inr_per_qtl ?? 2410.0;
  const totalDockage = commercial.total_dockage_inr_per_qtl ?? 0.0;
  const settlementTier = (commercial.settlement_tier ?? 'FULL_MSP_PAYOUT').replace(/_/g, ' ');
  const netLotPayout = commercial.estimated_net_payout_inr ?? (netRate * 50);
  const dockageItems: any[] = commercial.dockage_items ?? [];

  // Cold Storage Preservation Advisory
  const storageAdv = report.storage_advisory || {};
  const storageScore = storageAdv.mean_storageability_score ?? 85.0;
  const storageRec = (storageAdv.storage_recommendation ?? 'BUFFER_STOCK_PREMIUM').replace(/_/g, ' ');
  const storageDays = storageAdv.recommended_max_storage_days ?? 90;
  const storageRisk = storageAdv.respiration_risk_level ?? 'LOW';
  const storageAction = storageAdv.recommended_action ?? 'Approved for ventilated cold storage.';

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
      {/* Certificate Document Header */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.reportHeaderCard}>
          <View style={styles.badgeRow}>
            <Text style={styles.docTypeLabel}>CERTIFICATE OF INSPECTION · गुणवत्ता प्रमाणपत्र</Text>
            <Text style={styles.certDate}>
              {new Date(report.finalized_at || report.created_at).toLocaleDateString()}
            </Text>
          </View>
          <Text style={styles.certTitle}>Onion Quality Appraisal Record</Text>
          <Text style={styles.certSub}>
            Lot Assessment Complete • NAFED Procurement Protocol • भारत सरकार
          </Text>
        </View>
      </FadeInView>

      {/* Lot Metadata Card */}
      <FadeInView delay={100} distance={12}>
        <View style={styles.certCard}>
          <Text style={styles.sectionHeaderTitle}>Consignment Metadata · लॉट तपशील</Text>

          <View style={styles.metaGrid}>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Report ID:</Text>
              <Text style={styles.metaValueMono}>{report.report_id.slice(0, 18)}</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Lot Identifier:</Text>
              <Text style={[styles.metaValue, { color: Colors.accent }]}>
                {report.lot_id || 'N/A'}
              </Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>APMC Mandi:</Text>
              <Text style={styles.metaValue}>{report.procurement_centre || 'N/A'}</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Procurement Officer:</Text>
              <Text style={styles.metaValue}>{report.officer_name || 'N/A'}</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>Grading Standard:</Text>
              <Text style={styles.metaValueMono}>
                {report.ruleset_version.replace('BIS_IS_17912_2022', 'BIS IS 17912:2022')}
              </Text>
            </View>
          </View>
        </View>
      </FadeInView>

      {/* Lot Grade Distribution */}
      <FadeInView delay={150} distance={12}>
        <View style={styles.sectionCard}>
          <Text style={styles.sectionHeaderTitle}>Lot Grade Distribution · प्रतवारी वर्गीकरण</Text>

          <View style={styles.gradeRow}>
            <View style={styles.gradeLeft}>
              <View style={[styles.gradeDot, { backgroundColor: Colors.accent }]} />
              <Text style={styles.gradeName}>Grade A (Super · सुपर 45–65 mm)</Text>
            </View>
            <Text style={styles.gradeCount}>
              {report.grade_a_count} ({report.grade_a_pct.toFixed(1)}%)
            </Text>
          </View>

          <View style={styles.gradeRow}>
            <View style={styles.gradeLeft}>
              <View style={[styles.gradeDot, { backgroundColor: Colors.urs }]} />
              <Text style={styles.gradeName}>URS (Relaxed · मध्यम 35–70 mm)</Text>
            </View>
            <Text style={[styles.gradeCount, { color: Colors.urs }]}>
              {report.urs_count} ({report.urs_pct.toFixed(1)}%)
            </Text>
          </View>

          <View style={styles.gradeRow}>
            <View style={styles.gradeLeft}>
              <View style={[styles.gradeDot, { backgroundColor: Colors.reject }]} />
              <Text style={styles.gradeName}>Rejected (Off-Grade · रद्द / &lt;35 mm)</Text>
            </View>
            <Text style={[styles.gradeCount, { color: Colors.reject }]}>
              {report.rejected_count} ({report.rejected_pct.toFixed(1)}%)
            </Text>
          </View>

          <View style={[styles.gradeRow, styles.totalRow]}>
            <Text style={styles.totalLabel}>Total Representative Bulbs:</Text>
            <Text style={styles.totalValue}>{report.total_bulbs}</Text>
          </View>
        </View>
      </FadeInView>

      {/* Cold Storage Preservation Advisory */}
      <FadeInView delay={180} distance={12}>
        <View style={styles.sectionCard}>
          <View style={styles.cardHeaderRow}>
            <View>
              <Text style={styles.cardSectionTag}>AGRONOMIC STORAGE HEURISTIC · ICAR-DOGR INFORMED</Text>
              <Text style={styles.sectionHeaderTitle}>Cold Storage Survival Horizon · शीतगृह कालावधी</Text>
            </View>
            <View
              style={[
                styles.storageTierBadge,
                storageScore >= 80
                  ? styles.storageTierBadgeGood
                  : storageScore >= 60
                  ? styles.storageTierBadgeWarn
                  : styles.storageTierBadgeDanger,
              ]}
            >
              <Text
                style={[
                  styles.storageTierText,
                  storageScore >= 80
                    ? styles.storageTierTextGood
                    : storageScore >= 60
                    ? styles.storageTierTextWarn
                    : styles.storageTierTextDanger,
                ]}
              >
                {storageRec}
              </Text>
            </View>
          </View>

          <View style={styles.storageScoreHeroRow}>
            <View style={styles.storageScoreBox}>
              <Text style={styles.storageScoreLarge}>{storageScore.toFixed(0)}</Text>
              <Text style={styles.storageScoreOutOf}>/100</Text>
            </View>
            <View style={styles.storageHorizonBox}>
              <Text style={styles.storageHorizonLabel}>MAX SAFE STORAGE · सुरक्षित कालावधी</Text>
              <Text style={styles.storageHorizonDays}>{storageDays} Days</Text>
              <Text style={styles.storageHorizonSub}>0–2°C, 65–70% RH Cold Chamber</Text>
            </View>
          </View>

          <View style={styles.storageBiomarkerRow}>
            <View style={styles.biomarkerItem}>
              <Text style={styles.biomarkerLabel}>RESPIRATION</Text>
              <Text
                style={[
                  styles.biomarkerVal,
                  storageRisk === 'LOW'
                    ? { color: Colors.accentTeal }
                    : storageRisk === 'MEDIUM'
                    ? { color: Colors.urs }
                    : { color: Colors.reject },
                ]}
              >
                {storageRisk}
              </Text>
            </View>
            <View style={styles.biomarkerItem}>
              <Text style={styles.biomarkerLabel}>BLACK MOLD</Text>
              <Text style={styles.biomarkerVal}>
                {storageAdv.mean_black_mold_area_pct !== undefined
                  ? `${storageAdv.mean_black_mold_area_pct.toFixed(2)}%`
                  : '0.00%'}
              </Text>
            </View>
            <View style={styles.biomarkerItem}>
              <Text style={styles.biomarkerLabel}>TUNIC COVER</Text>
              <Text style={styles.biomarkerVal}>
                {storageAdv.mean_tunic_retention_pct !== undefined
                  ? `${storageAdv.mean_tunic_retention_pct.toFixed(1)}%`
                  : '94.2%'}
              </Text>
            </View>
          </View>

          <View style={styles.directiveBanner}>
            <Text style={styles.directiveTag}>NAFED ALLOCATION DIRECTIVE</Text>
            <Text style={styles.directiveText}>{storageAction}</Text>
          </View>
        </View>
      </FadeInView>

      {/* Commercial APMC Mandi Settlement Calculator */}
      <FadeInView delay={220} distance={12}>
        <View style={styles.sectionCard}>
          <View style={styles.cardHeaderRow}>
            <View>
              <Text style={styles.cardSectionTag}>APMC MANDI / PSF PROTOCOL</Text>
              <Text style={styles.sectionHeaderTitle}>Commercial Settlement Slip · बाजार भाव पावती</Text>
            </View>
            <View style={styles.tierPill}>
              <Text style={styles.tierPillText}>{settlementTier}</Text>
            </View>
          </View>

          <View style={styles.payoutHighlightRow}>
            <View style={styles.payoutMetricBlock}>
              <Text style={styles.payoutMetricLabel}>NET PAYOUT RATE</Text>
              <Text style={styles.payoutRateVal}>₹{netRate.toFixed(2)}</Text>
              <Text style={styles.payoutMetricSub}>per Quintal (100 kg)</Text>
            </View>
            <View style={styles.payoutDivider} />
            <View style={styles.payoutMetricBlock}>
              <Text style={styles.payoutMetricLabel}>EST. LOT PAYOUT</Text>
              <Text style={styles.payoutTotalVal}>
                ₹{netLotPayout.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </Text>
              <Text style={styles.payoutMetricSub}>50 Qtl Consignment</Text>
            </View>
          </View>

          <View style={styles.mspBenchmarkRow}>
            <Text style={styles.mspBenchmarkLabel}>Benchmark MSP (Price Stabilisation Fund):</Text>
            <Text style={styles.mspBenchmarkValue}>₹{baseMsp.toFixed(2)} / qtl</Text>
          </View>

          {dockageItems.length > 0 && (
            <View style={styles.dockageSubSection}>
              <View style={styles.dockageSubHeader}>
                <Text style={styles.dockageSubTitle}>FAQ Quality Dockage Deductions</Text>
                <Text style={styles.totalDockageBadge}>- ₹{totalDockage.toFixed(2)} / qtl</Text>
              </View>
              {dockageItems.map((item: any, idx: number) => (
                <View
                  key={idx}
                  style={[styles.dockageItemRow, idx % 2 === 1 && styles.dockageItemRowAlt]}
                >
                  <Text style={styles.dockageItemName}>{item.description || item.code}</Text>
                  <Text style={styles.dockageItemRate}>
                    {item.deduction_inr_per_qtl > 0
                      ? `- ₹${item.deduction_inr_per_qtl.toFixed(2)}`
                      : '₹0.00'}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </View>
      </FadeInView>

      {/* Defect Occurrences */}
      <FadeInView delay={250} distance={12}>
        <View style={styles.sectionCard}>
          <Text style={styles.sectionHeaderTitle}>Defect Appraisal Summary</Text>
          <View style={styles.defectGrid}>
            <View style={styles.defectCell}>
              <Text style={[styles.defectCount, { color: Colors.reject }]}>
                {report.defect_counts['rotten'] ?? 0}
              </Text>
              <Text style={styles.defectType}>Rotten</Text>
            </View>
            <View style={styles.defectCell}>
              <Text style={[styles.defectCount, { color: Colors.review }]}>
                {report.defect_counts['sprouted'] ?? 0}
              </Text>
              <Text style={styles.defectType}>Sprouted</Text>
            </View>
            <View style={styles.defectCell}>
              <Text style={[styles.defectCount, { color: Colors.urs }]}>
                {report.defect_counts['damaged'] ?? 0}
              </Text>
              <Text style={styles.defectType}>Damaged</Text>
            </View>
            <View style={styles.defectCell}>
              <Text style={[styles.defectCount, { color: Colors.accent }]}>
                {report.defect_counts['undersize'] ?? 0}
              </Text>
              <Text style={styles.defectType}>Goli / Small</Text>
            </View>
          </View>
        </View>
      </FadeInView>

      {/* Sovereign Cryptographic Seal & Verification Card */}
      <FadeInView delay={300} distance={12}>
        <View style={styles.sectionCard}>
          <View style={styles.sealCardHeader}>
            <View style={{ flex: 1, paddingRight: Spacing.sm }}>
              <Text style={styles.cardSectionTag}>TAMPER-PROOF METROLOGY</Text>
              <Text style={styles.sectionHeaderTitle}>Sovereign Cryptographic Seal · डिजिटल मुहर</Text>
            </View>
            <View
              style={[
                styles.sealStatusBadge,
                (report.seal_status === 'VALID_SEALED' || report.seal_status === 'SEALED_DEMO_SAMPLE')
                  ? styles.sealStatusBadgeValid
                  : report.seal_status === 'INVALID_MISSING_PHOTO'
                  ? styles.sealStatusBadgeInvalid
                  : styles.sealStatusBadgePending,
              ]}
            >
              <Feather
                name={
                  (report.seal_status === 'VALID_SEALED' || report.seal_status === 'SEALED_DEMO_SAMPLE')
                    ? 'shield'
                    : report.seal_status === 'INVALID_MISSING_PHOTO'
                    ? 'alert-triangle'
                    : 'clock'
                }
                size={11}
                color={
                  (report.seal_status === 'VALID_SEALED' || report.seal_status === 'SEALED_DEMO_SAMPLE')
                    ? '#059669'
                    : report.seal_status === 'INVALID_MISSING_PHOTO'
                    ? '#dc2626'
                    : '#d97706'
                }
              />
              <Text
                style={[
                  styles.sealStatusText,
                  (report.seal_status === 'VALID_SEALED' || report.seal_status === 'SEALED_DEMO_SAMPLE')
                    ? styles.sealStatusTextValid
                    : report.seal_status === 'INVALID_MISSING_PHOTO'
                    ? styles.sealStatusTextInvalid
                    : styles.sealStatusTextPending,
                ]}
              >
                {report.seal_status || 'SEALED'}
              </Text>
            </View>
          </View>

          <Text style={styles.shareDesc}>
            Immutable HMAC-SHA256 signature binding lot grading metrics, raw optical photo SHA-256 digest, and officer credentials:
          </Text>

          {/* HMAC Sovereign Seal */}
          <View style={styles.hashContainer}>
            <View style={styles.hashHeaderRow}>
              <Text style={styles.hashLabel}>HMAC-SHA256 LOT SIGNATURE</Text>
              <Feather name="lock" size={11} color={Colors.textMuted} />
            </View>
            <Text style={styles.hashValue} selectable>
              {report.cryptographic_seal || report.integrity_hash || 'PENDING_FINALIZATION'}
            </Text>
          </View>

          {/* Optical Photo Digest */}
          {report.image_sha256 ? (
            <View style={[styles.hashContainer, { marginTop: Spacing.xs }]}>
              <View style={styles.hashHeaderRow}>
                <Text style={styles.hashLabel}>OPTICAL RAW PHOTO SHA-256</Text>
                <Feather name="image" size={11} color={Colors.textMuted} />
              </View>
              <Text style={styles.hashValue} selectable>
                {report.image_sha256}
              </Text>
            </View>
          ) : null}

          {/* Online Verification Web Audit Action */}
          <AnimatedPressable
            haptic="medium"
            style={styles.verifySealBtn}
            onPress={handleVerifySealOnline}
          >
            <View style={styles.verifySealBtnContent}>
              <Feather name="check-circle" size={14} color="#059669" />
              <Text style={styles.verifySealBtnText}>Verify Mathematical Proof Online</Text>
              <Feather name="external-link" size={12} color="#059669" />
            </View>
          </AnimatedPressable>

          {/* Public Certificate QR Link */}
          {report.share_url ? (
            <View style={{ marginTop: Spacing.sm }}>
              <Text style={[styles.hashLabel, { marginBottom: 4 }]}>PUBLIC ASSAY CERTIFICATE LINK</Text>
              <AnimatedPressable
                haptic="selection"
                style={styles.shareLinkBox}
                onPress={handleOpenShareLink}
              >
                <Feather name="link" size={12} color={Colors.textMuted} style={{ marginRight: 6 }} />
                <Text style={styles.shareLinkText} numberOfLines={1}>
                  {report.share_url}
                </Text>
              </AnimatedPressable>
            </View>
          ) : null}
        </View>
      </FadeInView>

      {/* Mandatory Audit Disclaimer */}
      <FadeInView delay={350} distance={12}>
        <View style={styles.disclaimerCard}>
          <Text style={styles.disclaimerTitle}>Regulatory Disclaimer</Text>
          <Text style={styles.disclaimerText}>{report.limitations_note}</Text>
        </View>
      </FadeInView>

      {/* Primary Action Buttons */}
      <FadeInView delay={400} distance={15}>
        <View style={styles.btnColumn}>
          <AnimatedPressable
            haptic="heavy"
            style={styles.pdfBtn}
            onPress={handleDownloadPdf}
          >
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <Feather name="download" size={15} color="#ffffff" />
              <Text style={styles.pdfBtnText}>Download Official PDF Certificate</Text>
            </View>
          </AnimatedPressable>

          <View style={{ flexDirection: 'row', gap: Spacing.sm }}>
            <AnimatedPressable
              haptic="medium"
              style={[styles.nextBtn, { flex: 1, backgroundColor: '#f0fdf4', borderColor: '#bbf7d0' }]}
              onPress={() => handleBhashiniAnnounce('hi')}
              disabled={announcing}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                <Feather name="volume-2" size={14} color="#16a34a" />
                <Text style={[styles.nextBtnText, { color: '#16a34a' }]}>
                  {announcing ? 'Playing...' : 'Mandi Audio'}
                </Text>
              </View>
            </AnimatedPressable>

            <AnimatedPressable
              haptic="light"
              style={[styles.nextBtn, { flex: 1, backgroundColor: '#eff6ff', borderColor: '#bfdbfe' }]}
              onPress={handleExportEnam}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                <Feather name="file-text" size={14} color="#2563eb" />
                <Text style={[styles.nextBtnText, { color: '#2563eb' }]}>eNAM Assaying</Text>
              </View>
            </AnimatedPressable>
          </View>

          <AnimatedPressable
            haptic="medium"
            style={styles.nextBtn}
            onPress={onStartNewInspection}
          >
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
              <Text style={styles.nextBtnText}>Start Next Lot Inspection</Text>
              <Feather name="arrow-right" size={14} color="#059669" />
            </View>
          </AnimatedPressable>
        </View>
      </FadeInView>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  scrollContent: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.hero,
    gap: Spacing.md,
  },
  centerContainer: {
    flex: 1,
    backgroundColor: Colors.bg,
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.xl,
  },
  loadingText: {
    ...Typography.title2,
    marginTop: Spacing.md,
  },
  loadingSub: {
    color: Colors.textMuted,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
    maxWidth: 320,
  },
  reportHeaderCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.sm,
  },
  badgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  docTypeLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.8,
  },
  certDate: {
    fontSize: 11,
    color: Colors.textDim,
    fontFamily: 'monospace',
  },
  certTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text,
    letterSpacing: -0.2,
  },
  certSub: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: 2,
  },
  certCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.sm,
  },
  sectionHeaderTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  metaGrid: {
    gap: 6,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderMuted,
  },
  metaLabel: {
    fontSize: 12,
    color: Colors.textMuted,
  },
  metaValue: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.text,
  },
  metaValueMono: {
    fontSize: 11,
    fontFamily: 'monospace',
    color: Colors.textSecondary,
  },
  sectionCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.sm,
  },
  gradeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderMuted,
  },
  gradeLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  gradeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  gradeName: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  gradeCount: {
    fontSize: 12,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  totalRow: {
    borderBottomWidth: 0,
    marginTop: 6,
    paddingTop: 8,
  },
  totalLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.text,
  },
  totalValue: {
    fontSize: 14,
    fontWeight: '800',
    color: Colors.accent,
    fontFamily: 'monospace',
  },
  settlementGrid: {
    gap: 6,
    marginTop: 4,
  },
  settlementRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  settlementLabel: {
    fontSize: 12,
    color: Colors.textMuted,
  },
  settlementValue: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.text,
    fontFamily: 'monospace',
  },
  payoutRow: {
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
    paddingTop: 8,
    marginTop: 4,
  },
  payoutLabel: {
    fontSize: 13,
    fontWeight: '800',
    color: Colors.text,
  },
  payoutValue: {
    fontSize: 15,
    fontWeight: '800',
    color: Colors.text,
    fontFamily: 'monospace',
  },
  defectGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Spacing.sm,
    marginTop: 4,
  },
  defectCell: {
    flex: 1,
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.sm,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  defectCount: {
    fontSize: 16,
    fontWeight: '800',
    fontFamily: 'monospace',
  },
  defectType: {
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 2,
    fontWeight: '600',
  },
  shareDesc: {
    fontSize: 12,
    color: Colors.textMuted,
    marginBottom: Spacing.sm,
    lineHeight: 17,
  },
  shareLinkBox: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  shareLinkText: {
    fontSize: 12,
    color: Colors.textSecondary,
    fontFamily: 'monospace',
  },
  disclaimerCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.sm,
  },
  disclaimerTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.5,
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  disclaimerText: {
    fontSize: 11,
    color: Colors.textMuted,
    lineHeight: 16,
  },
  btnColumn: {
    gap: Spacing.md,
    marginTop: Spacing.sm,
  },
  pdfBtn: {
    backgroundColor: Colors.accent,
    paddingVertical: 14,
    borderRadius: Radius.md,
    alignItems: 'center',
  },
  pdfBtnText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  nextBtn: {
    backgroundColor: Colors.cardBg,
    paddingVertical: 14,
    borderRadius: Radius.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.sm,
  },
  nextBtnText: {
    color: Colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  failGlowBadge: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.rejectBg,
    borderWidth: 2,
    borderColor: Colors.reject,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  failIcon: {
    fontSize: 24,
    color: Colors.reject,
    fontWeight: '800',
  },
  errorTitle: {
    ...Typography.title1,
    color: Colors.reject,
  },
  errorDesc: {
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
  },
  errorBtnRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginTop: Spacing.lg,
  },
  retryBtnPrimary: {
    backgroundColor: Colors.accent,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
  },
  retryBtnPrimaryText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 13,
  },
  retryBtn: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  retryBtnText: {
    color: Colors.text,
    fontWeight: '600',
    fontSize: 13,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.sm,
  },
  cardSectionTag: {
    fontSize: 9.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.accentTeal,
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  storageTierBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.xs,
    borderWidth: 1,
  },
  storageTierBadgeGood: {
    backgroundColor: 'rgba(15, 118, 110, 0.1)',
    borderColor: 'rgba(15, 118, 110, 0.3)',
  },
  storageTierBadgeWarn: {
    backgroundColor: 'rgba(217, 119, 6, 0.1)',
    borderColor: 'rgba(217, 119, 6, 0.3)',
  },
  storageTierBadgeDanger: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
  },
  storageTierText: {
    fontSize: 10,
    fontWeight: '800',
    fontFamily: 'monospace',
    letterSpacing: 0.3,
  },
  storageTierTextGood: { color: Colors.accentTeal },
  storageTierTextWarn: { color: Colors.urs },
  storageTierTextDanger: { color: Colors.reject },
  storageScoreHeroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginVertical: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  storageScoreBox: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginRight: Spacing.lg,
    paddingRight: Spacing.md,
    borderRightWidth: 1,
    borderRightColor: Colors.border,
  },
  storageScoreLarge: {
    fontSize: 34,
    fontWeight: '800',
    color: Colors.text,
    fontFamily: 'monospace',
  },
  storageScoreOutOf: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.textMuted,
    fontFamily: 'monospace',
    marginLeft: 2,
  },
  storageHorizonBox: {
    flex: 1,
  },
  storageHorizonLabel: {
    fontSize: 9,
    fontWeight: '700',
    color: Colors.textMuted,
    fontFamily: 'monospace',
    letterSpacing: 0.4,
  },
  storageHorizonDays: {
    fontSize: 20,
    fontWeight: '800',
    color: Colors.accentTeal,
    marginVertical: 1,
  },
  storageHorizonSub: {
    fontSize: 10.5,
    color: Colors.textSecondary,
  },
  storageBiomarkerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.sm,
    padding: Spacing.sm,
    marginTop: Spacing.xs,
  },
  biomarkerItem: {
    alignItems: 'center',
    flex: 1,
  },
  biomarkerLabel: {
    fontSize: 8.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    marginBottom: 2,
  },
  biomarkerVal: {
    fontSize: 12,
    fontWeight: '800',
    fontFamily: 'monospace',
    color: Colors.text,
  },
  directiveBanner: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.sm,
    padding: Spacing.sm,
    marginTop: Spacing.sm,
    borderLeftWidth: 3,
    borderLeftColor: Colors.accentTeal,
  },
  directiveTag: {
    fontSize: 8.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    marginBottom: 2,
  },
  directiveText: {
    fontSize: 11.5,
    color: Colors.text,
    lineHeight: 16,
    fontWeight: '500',
  },
  tierPill: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tierPillText: {
    fontSize: 10,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.accentTeal,
  },
  payoutHighlightRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.md,
    marginVertical: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  payoutMetricBlock: {
    flex: 1,
  },
  payoutDivider: {
    width: 1,
    height: '80%',
    backgroundColor: Colors.border,
    marginHorizontal: Spacing.md,
  },
  payoutMetricLabel: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.4,
  },
  payoutRateVal: {
    fontSize: 20,
    fontWeight: '800',
    color: Colors.accentTeal,
    fontFamily: 'monospace',
    marginVertical: 2,
  },
  payoutTotalVal: {
    fontSize: 20,
    fontWeight: '800',
    color: Colors.text,
    fontFamily: 'monospace',
    marginVertical: 2,
  },
  payoutMetricSub: {
    fontSize: 10,
    color: Colors.textDim,
  },
  mspBenchmarkRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: Spacing.sm,
    paddingTop: Spacing.xs,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
  },
  mspBenchmarkLabel: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  mspBenchmarkValue: {
    fontSize: 11,
    fontWeight: '700',
    fontFamily: 'monospace',
    color: Colors.textSecondary,
  },
  dockageSubSection: {
    marginTop: Spacing.sm,
    paddingTop: Spacing.xs,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
  },
  dockageSubHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  dockageSubTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textSecondary,
  },
  totalDockageBadge: {
    fontSize: 11,
    fontWeight: '800',
    fontFamily: 'monospace',
    color: Colors.reject,
  },
  dockageItemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 5,
    paddingHorizontal: 6,
    borderRadius: Radius.xs,
  },
  dockageItemRowAlt: {
    backgroundColor: Colors.cardBgElevated,
  },
  dockageItemName: {
    fontSize: 11,
    color: Colors.text,
    fontWeight: '500',
  },
  dockageItemRate: {
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.reject,
  },
  hashContainer: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: Spacing.sm,
    marginTop: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  hashLabel: {
    fontSize: 8.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  hashValue: {
    fontSize: 10,
    fontFamily: 'monospace',
    color: Colors.accentTeal,
    fontWeight: '600',
  },
  sealCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.xs,
  },
  sealStatusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.xs,
    borderWidth: 1,
    gap: 4,
  },
  sealStatusBadgeValid: {
    backgroundColor: '#ecfdf5',
    borderColor: '#a7f3d0',
  },
  sealStatusBadgeInvalid: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  sealStatusBadgePending: {
    backgroundColor: '#fffbeb',
    borderColor: '#fde68a',
  },
  sealStatusText: {
    fontSize: 9.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  sealStatusTextValid: {
    color: '#059669',
  },
  sealStatusTextInvalid: {
    color: '#dc2626',
  },
  sealStatusTextPending: {
    color: '#d97706',
  },
  hashHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  verifySealBtn: {
    marginTop: Spacing.sm,
    backgroundColor: '#ecfdf5',
    borderWidth: 1,
    borderColor: '#a7f3d0',
    borderRadius: Radius.sm,
    paddingVertical: 10,
    paddingHorizontal: 12,
  },
  verifySealBtnContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  verifySealBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#059669',
  },
});
