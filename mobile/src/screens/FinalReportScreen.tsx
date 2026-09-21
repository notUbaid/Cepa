import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { getApiBaseUrl } from '../config';
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

  useEffect(() => {
    const fetchOrCreateReport = async () => {
      try {
        setLoading(true);
        const rep = await ApiClient.generateReport(inspection.id);
        setReport(rep);
        Haptics.success();
      } catch (err: any) {
        setError(err.message);
        Haptics.error();
      } finally {
        setLoading(false);
      }
    };

    fetchOrCreateReport();
  }, [inspection.id]);

  const handleDownloadPdf = () => {
    Haptics.heavy();
    const pdfUrl = `${getApiBaseUrl()}/api/v1/inspections/${inspection.id}/reports/pdf`;
    Linking.openURL(pdfUrl).catch((e) => {
      Haptics.error();
      alert(`Could not open PDF: ${e.message}`);
    });
  };

  const handleOpenShareLink = () => {
    if (report?.share_url) {
      Haptics.light();
      Linking.openURL(report.share_url).catch((e) =>
        alert(`Could not open link: ${e.message}`)
      );
    }
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
          <Text style={styles.failIcon}>✕</Text>
        </View>
        <Text style={styles.errorTitle}>Report Generation Failed</Text>
        <Text style={styles.errorDesc}>{error}</Text>
        <AnimatedPressable
          haptic="medium"
          style={styles.retryBtn}
          onPress={onStartNewInspection}
        >
          <Text style={styles.retryBtnText}>Return to Home</Text>
        </AnimatedPressable>
      </View>
    );
  }

  // Commercial rate deduction calculation (NAFED MSP 2024-2026: ₹1,800/qtl base)
  const baseMsp = 1800;
  const rejectPct = report.rejected_pct;
  const dockageRate = rejectPct > 5.0 ? Math.min(350, (rejectPct - 5.0) * 25) : 0;
  const netProcurementPayout = Math.max(800, baseMsp - dockageRate);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
      {/* Celebration Header */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.celebrationBanner}>
          <View style={styles.certStamp}>
            <Text style={styles.certStampIcon}>✓</Text>
          </View>
          <View style={styles.certHeaderInfo}>
            <View style={styles.badgeRow}>
              <View style={styles.verifiedPill}>
                <Text style={styles.verifiedPillText}>CERTIFICATE ISSUED</Text>
              </View>
              <Text style={styles.certDate}>
                {new Date(report.finalized_at || report.created_at).toLocaleDateString()}
              </Text>
            </View>
            <Text style={styles.certTitle}>Onion Quality Appraisal Record</Text>
            <Text style={styles.certSub}>
              Cepa Quality Record • Mandi Procurement Protocol
            </Text>
          </View>
        </View>
      </FadeInView>

      {/* Lot Metadata Card */}
      <FadeInView delay={100} distance={12}>
        <View style={styles.certCard}>
          <Text style={styles.sectionHeaderTitle}>Consignment Metadata</Text>

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
              <Text style={[styles.metaValueMono, { color: Colors.gradeA }]}>
                {report.ruleset_version.replace('BIS_IS_17912_2022', 'BIS IS 17912:2022')}
              </Text>
            </View>
          </View>
        </View>
      </FadeInView>

      {/* Lot Grade Distribution */}
      <FadeInView delay={150} distance={12}>
        <View style={styles.sectionCard}>
          <Text style={styles.sectionHeaderTitle}>Lot Grade Distribution</Text>

          <View style={styles.gradeRow}>
            <View style={styles.gradeLeft}>
              <View style={[styles.gradeDot, { backgroundColor: Colors.gradeA }]} />
              <Text style={styles.gradeName}>Grade A (Super 45–65 mm)</Text>
            </View>
            <Text style={[styles.gradeCount, { color: Colors.gradeA }]}>
              {report.grade_a_count} ({report.grade_a_pct.toFixed(1)}%)
            </Text>
          </View>

          <View style={styles.gradeRow}>
            <View style={styles.gradeLeft}>
              <View style={[styles.gradeDot, { backgroundColor: Colors.urs }]} />
              <Text style={styles.gradeName}>URS (Under Rejection Standard 35–70 mm)</Text>
            </View>
            <Text style={[styles.gradeCount, { color: Colors.urs }]}>
              {report.urs_count} ({report.urs_pct.toFixed(1)}%)
            </Text>
          </View>

          <View style={styles.gradeRow}>
            <View style={styles.gradeLeft}>
              <View style={[styles.gradeDot, { backgroundColor: Colors.reject }]} />
              <Text style={styles.gradeName}>Rejected (Rotten / Under 35 mm)</Text>
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

      {/* Commercial NAFED Settlement Calculator */}
      <FadeInView delay={200} distance={12}>
        <View style={styles.sectionCard}>
          <Text style={styles.sectionHeaderTitle}>Commercial Settlement Estimate</Text>
          <View style={styles.settlementGrid}>
            <View style={styles.settlementRow}>
              <Text style={styles.settlementLabel}>Benchmark MSP (Nashik FAQ):</Text>
              <Text style={styles.settlementValue}>₹{baseMsp.toLocaleString()}/qtl</Text>
            </View>
            <View style={styles.settlementRow}>
              <Text style={styles.settlementLabel}>Dockage Deduction ({rejectPct.toFixed(1)}% Rejection):</Text>
              <Text style={[styles.settlementValue, { color: dockageRate > 0 ? Colors.reject : Colors.gradeA }]}>
                {dockageRate > 0 ? `- ₹${dockageRate.toFixed(0)}/qtl` : '₹0/qtl (Full FAQ Pass)'}
              </Text>
            </View>
            <View style={[styles.settlementRow, styles.payoutRow]}>
              <Text style={styles.payoutLabel}>Net Procurement Payout:</Text>
              <Text style={styles.payoutValue}>₹{netProcurementPayout.toFixed(0)}/qtl</Text>
            </View>
          </View>
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

      {/* Share / Verification Link Card */}
      <FadeInView delay={300} distance={12}>
        <View style={styles.sectionCard}>
          <Text style={styles.sectionHeaderTitle}>Online Verification & Audit</Text>
          <Text style={styles.shareDesc}>
            Mandi commissioners and farmers can view this immutable inspection audit online:
          </Text>
          <AnimatedPressable
            haptic="selection"
            style={styles.shareLinkBox}
            onPress={handleOpenShareLink}
          >
            <Text style={styles.shareLinkText} numberOfLines={1}>
              {report.share_url}
            </Text>
          </AnimatedPressable>
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
            <Text style={styles.pdfBtnText}>Download Official PDF Certificate</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="medium"
            style={styles.nextBtn}
            onPress={onStartNewInspection}
          >
            <Text style={styles.nextBtnText}>Start Next Lot Inspection →</Text>
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
  celebrationBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.md,
    ...Shadows.sm,
  },
  certStamp: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.gradeABg,
    borderWidth: 1,
    borderColor: Colors.gradeA,
    justifyContent: 'center',
    alignItems: 'center',
  },
  certStampIcon: {
    fontSize: 20,
    fontWeight: '700',
    color: Colors.gradeA,
  },
  certHeaderInfo: {
    flex: 1,
  },
  badgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  verifiedPill: {
    backgroundColor: Colors.gradeABg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: Colors.gradeA,
  },
  verifiedPillText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.gradeA,
    letterSpacing: 0.5,
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
    color: Colors.gradeA,
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
  retryBtn: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
    marginTop: Spacing.lg,
  },
  retryBtnText: {
    color: Colors.text,
    fontWeight: '700',
  },
});
