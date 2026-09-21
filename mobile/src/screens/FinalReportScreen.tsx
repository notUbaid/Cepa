import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { getApiBaseUrl } from '../config';
import { InspectionDetail, ReportDetail } from '../types';

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
        // Attempt to generate or retrieve report
        const rep = await ApiClient.generateReport(inspection.id);
        setReport(rep);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchOrCreateReport();
  }, [inspection.id]);

  const handleDownloadPdf = () => {
    const pdfUrl = `${getApiBaseUrl()}/api/v1/inspections/${inspection.id}/reports/pdf`;
    Linking.openURL(pdfUrl).catch((e) => alert(`Could not open PDF: ${e.message}`));
  };

  const handleOpenShareLink = () => {
    if (report?.share_url) {
      Linking.openURL(report.share_url).catch((e) =>
        alert(`Could not open link: ${e.message}`)
      );
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
        <Text style={styles.loadingText}>Compiling official PDF report...</Text>
      </View>
    );
  }

  if (error || !report) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorTitle}>Report Generation Failed</Text>
        <Text style={styles.errorDesc}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={onStartNewInspection}>
          <Text style={styles.retryBtnText}>Return to Home</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
      {/* Official Certificate Header */}
      <View style={styles.certCard}>
        <Text style={styles.certBadge}>FINAL INSPECTION RECORD</Text>
        <Text style={styles.certTitle}>Onion Quality Appraisal Report</Text>
        <Text style={styles.certSub}>
          Cepa Inspection System • SIH26031 Proof of Concept
        </Text>

        <View style={styles.metaGrid}>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Report ID:</Text>
            <Text style={styles.metaValue}>{report.report_id.slice(0, 13)}...</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Lot ID:</Text>
            <Text style={styles.metaValue}>{report.lot_id || 'N/A'}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Procurement Centre:</Text>
            <Text style={styles.metaValue}>{report.procurement_centre || 'N/A'}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Officer:</Text>
            <Text style={styles.metaValue}>{report.officer_name || 'N/A'}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Active Policy:</Text>
            <Text style={[styles.metaValue, { color: '#38bdf8' }]}>
              {report.ruleset_version}
            </Text>
          </View>
        </View>
      </View>

      {/* Lot Grading Summary Table */}
      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Lot Grade Distribution</Text>

        <View style={styles.gradeRow}>
          <View style={styles.gradeLeft}>
            <View style={[styles.gradeDot, { backgroundColor: '#27ae60' }]} />
            <Text style={styles.gradeName}>Grade A (45–65 mm)</Text>
          </View>
          <Text style={styles.gradeCount}>
            {report.grade_a_count} ({report.grade_a_pct.toFixed(1)}%)
          </Text>
        </View>

        <View style={styles.gradeRow}>
          <View style={styles.gradeLeft}>
            <View style={[styles.gradeDot, { backgroundColor: '#f39c12' }]} />
            <Text style={styles.gradeName}>URS (35–70 mm)</Text>
          </View>
          <Text style={styles.gradeCount}>
            {report.urs_count} ({report.urs_pct.toFixed(1)}%)
          </Text>
        </View>

        <View style={styles.gradeRow}>
          <View style={styles.gradeLeft}>
            <View style={[styles.gradeDot, { backgroundColor: '#e74c3c' }]} />
            <Text style={styles.gradeName}>Rejected (Rot / Size)</Text>
          </View>
          <Text style={styles.gradeCount}>
            {report.rejected_count} ({report.rejected_pct.toFixed(1)}%)
          </Text>
        </View>

        <View style={styles.gradeRow}>
          <View style={styles.gradeLeft}>
            <View style={[styles.gradeDot, { backgroundColor: '#3498db' }]} />
            <Text style={styles.gradeName}>Review Required</Text>
          </View>
          <Text style={styles.gradeCount}>{report.review_count}</Text>
        </View>

        <View style={[styles.gradeRow, styles.totalRow]}>
          <Text style={styles.totalLabel}>Total Bulbs Inspected:</Text>
          <Text style={styles.totalValue}>{report.total_bulbs}</Text>
        </View>
      </View>

      {/* Defect Counts */}
      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Visible Defect Occurrences</Text>
        <View style={styles.defectGrid}>
          <View style={styles.defectCell}>
            <Text style={styles.defectCount}>
              {report.defect_counts['rotten'] ?? 0}
            </Text>
            <Text style={styles.defectType}>Rotten</Text>
          </View>
          <View style={styles.defectCell}>
            <Text style={styles.defectCount}>
              {report.defect_counts['sprouted'] ?? 0}
            </Text>
            <Text style={styles.defectType}>Sprouted</Text>
          </View>
          <View style={styles.defectCell}>
            <Text style={styles.defectCount}>
              {report.defect_counts['damaged'] ?? 0}
            </Text>
            <Text style={styles.defectType}>Damaged</Text>
          </View>
          <View style={styles.defectCell}>
            <Text style={styles.defectCount}>
              {report.defect_counts['undersize'] ?? 0}
            </Text>
            <Text style={styles.defectType}>Undersized</Text>
          </View>
        </View>
      </View>

      {/* Share / Verification Link Card */}
      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Certificate Verification & Sharing</Text>
        <Text style={styles.shareDesc}>
          Farmers and mandi officers can view this audit record online without login:
        </Text>
        <TouchableOpacity style={styles.shareLinkBox} onPress={handleOpenShareLink}>
          <Text style={styles.shareLinkText} numberOfLines={1}>
            🔗 {report.share_url}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Mandatory Limitations Disclaimer */}
      <View style={styles.disclaimerCard}>
        <Text style={styles.disclaimerTitle}>MANDATORY AUDIT DISCLAIMER</Text>
        <Text style={styles.disclaimerText}>{report.limitations_note}</Text>
      </View>

      {/* Actions */}
      <View style={styles.btnColumn}>
        <TouchableOpacity style={styles.pdfBtn} onPress={handleDownloadPdf}>
          <Text style={styles.pdfBtnText}>📄 Download Official PDF Certificate</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.nextBtn} onPress={onStartNewInspection}>
          <Text style={styles.nextBtnText}>+ Start Next Inspection</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1b2a',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
    gap: 14,
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#0d1b2a',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 12,
    fontSize: 13,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#e74c3c',
  },
  errorDesc: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 6,
    textAlign: 'center',
  },
  retryBtn: {
    backgroundColor: '#334155',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    marginTop: 16,
  },
  retryBtnText: {
    color: '#fff',
    fontWeight: '700',
  },
  certCard: {
    backgroundColor: '#1b263b',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2e3d52',
  },
  certBadge: {
    fontSize: 10,
    fontWeight: '800',
    color: '#2ecc71',
    letterSpacing: 1,
  },
  certTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#f8f9fa',
    marginTop: 4,
  },
  certSub: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
    marginBottom: 12,
  },
  metaGrid: {
    borderTopWidth: 1,
    borderTopColor: '#243347',
    paddingTop: 8,
    gap: 4,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metaLabel: {
    fontSize: 11,
    color: '#94a3b8',
  },
  metaValue: {
    fontSize: 11,
    fontWeight: '700',
    color: '#e2e8f0',
  },
  sectionCard: {
    backgroundColor: '#1b263b',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#243347',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: '#cbd5e1',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 10,
  },
  gradeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#243347',
  },
  gradeLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  gradeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  gradeName: {
    fontSize: 12,
    color: '#f8f9fa',
    fontWeight: '600',
  },
  gradeCount: {
    fontSize: 12,
    fontWeight: '700',
    color: '#f8f9fa',
  },
  totalRow: {
    borderBottomWidth: 0,
    paddingTop: 10,
  },
  totalLabel: {
    fontSize: 12,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  totalValue: {
    fontSize: 14,
    fontWeight: '800',
    color: '#38bdf8',
  },
  defectGrid: {
    flexDirection: 'row',
    gap: 8,
  },
  defectCell: {
    flex: 1,
    backgroundColor: '#0d1b2a',
    borderRadius: 8,
    padding: 8,
    alignItems: 'center',
  },
  defectCount: {
    fontSize: 16,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  defectType: {
    fontSize: 10,
    color: '#94a3b8',
    marginTop: 2,
  },
  shareDesc: {
    fontSize: 11,
    color: '#94a3b8',
    marginBottom: 8,
    lineHeight: 16,
  },
  shareLinkBox: {
    backgroundColor: '#0d1b2a',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  shareLinkText: {
    color: '#38bdf8',
    fontSize: 11,
  },
  disclaimerCard: {
    backgroundColor: 'rgba(231, 76, 60, 0.1)',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: 'rgba(231, 76, 60, 0.3)',
  },
  disclaimerTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: '#ff7675',
    marginBottom: 4,
  },
  disclaimerText: {
    fontSize: 10,
    color: '#fca5a5',
    lineHeight: 15,
  },
  btnColumn: {
    gap: 10,
    marginTop: 4,
  },
  pdfBtn: {
    backgroundColor: '#0284c7',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
  },
  pdfBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '800',
  },
  nextBtn: {
    backgroundColor: '#1b263b',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  nextBtnText: {
    color: '#cbd5e1',
    fontSize: 12,
    fontWeight: '700',
  },
});
