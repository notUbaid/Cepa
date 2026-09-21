import React, { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { OnionInstanceDetail } from '../types';

interface EvidenceDrilldownModalProps {
  visible: boolean;
  onion: OnionInstanceDetail | null;
  inspectionId: string;
  onClose: () => void;
  onCorrectionSaved: (updatedOnion: OnionInstanceDetail) => void;
}

export const EvidenceDrilldownModal: React.FC<EvidenceDrilldownModalProps> = ({
  visible,
  onion,
  inspectionId,
  onClose,
  onCorrectionSaved,
}) => {
  if (!onion) return null;

  const [showMask, setShowMask] = useState(false);
  const [isCorrecting, setIsCorrecting] = useState(false);
  const [damagedInput, setDamagedInput] = useState(
    ((onion.damaged_prob ?? 0) * 100).toFixed(0)
  );
  const [rottenInput, setRottenInput] = useState(
    ((onion.rotten_prob ?? 0) * 100).toFixed(0)
  );
  const [sproutedInput, setSproutedInput] = useState(
    ((onion.sprouted_prob ?? 0) * 100).toFixed(0)
  );
  const [officerRemarks, setOfficerRemarks] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSaveCorrection = async () => {
    setSaving(true);
    try {
      const updated = await ApiClient.correctOnion(inspectionId, onion.id, {
        damaged_prob: Math.min(1.0, Math.max(0.0, parseFloat(damagedInput) / 100)),
        rotten_prob: Math.min(1.0, Math.max(0.0, parseFloat(rottenInput) / 100)),
        sprouted_prob: Math.min(1.0, Math.max(0.0, parseFloat(sproutedInput) / 100)),
        corrected_by: 'Procurement Officer',
        notes: officerRemarks || undefined,
      });
      setIsCorrecting(false);
      onCorrectionSaved(updated);
    } catch (err: any) {
      alert(`Correction failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const getGradeColor = (grade: string | null) => {
    switch (grade) {
      case 'GRADE_A':
        return '#27ae60';
      case 'URS':
        return '#f39c12';
      case 'REJECTED':
        return '#e74c3c';
      default:
        return '#3498db';
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true}>
      <View style={styles.overlay}>
        <View style={styles.modalCard}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text style={styles.headerTitle}>Onion #{onion.display_number}</Text>
              <Text style={styles.headerSubtitle}>
                Confidence: {(onion.segmentation_conf * 100).toFixed(0)}% • Tier:{' '}
                {onion.confidence_tier}
              </Text>
            </View>
            <View style={styles.headerRight}>
              <View
                style={[
                  styles.gradePill,
                  { backgroundColor: getGradeColor(onion.grade) },
                ]}
              >
                <Text style={styles.gradePillText}>{onion.grade || 'PENDING'}</Text>
              </View>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Text style={styles.closeButtonText}>✕</Text>
              </TouchableOpacity>
            </View>
          </View>

          <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent}>
            {/* Visual Evidence Toggle */}
            <View style={styles.imageCard}>
              <View style={styles.toggleRow}>
                <TouchableOpacity
                  style={[styles.toggleBtn, !showMask && styles.toggleBtnActive]}
                  onPress={() => setShowMask(false)}
                >
                  <Text
                    style={[
                      styles.toggleBtnText,
                      !showMask && styles.toggleBtnTextActive,
                    ]}
                  >
                    Isolated Bulb Crop
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleBtn, showMask && styles.toggleBtnActive]}
                  onPress={() => setShowMask(true)}
                >
                  <Text
                    style={[
                      styles.toggleBtnText,
                      showMask && styles.toggleBtnTextActive,
                    ]}
                  >
                    Binary Mask
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.imageWrapper}>
                {showMask ? (
                  onion.mask_url ? (
                    <Image
                      source={{ uri: onion.mask_url }}
                      style={styles.cropImage}
                      resizeMode="contain"
                    />
                  ) : (
                    <View style={styles.noImage}>
                      <Text style={styles.noImageText}>Mask Not Available</Text>
                    </View>
                  )
                ) : onion.crop_url ? (
                  <Image
                    source={{ uri: onion.crop_url }}
                    style={styles.cropImage}
                    resizeMode="contain"
                  />
                ) : (
                  <View style={styles.noImage}>
                    <Text style={styles.noImageText}>Crop Not Available</Text>
                  </View>
                )}
              </View>

              {onion.touches_border && (
                <View style={styles.warningBox}>
                  <Text style={styles.warningText}>
                    ⚠️ Bulb touches image frame boundary. Sizing may be truncated.
                  </Text>
                </View>
              )}
            </View>

            {/* Geometric Size Measurement */}
            <View style={styles.sectionCard}>
              <Text style={styles.sectionTitle}>Physical Sizing (ChArUco Calibrated)</Text>
              <View style={styles.metricRow}>
                <Text style={styles.metricLabel}>Equivalent Diameter ($D_e$):</Text>
                <Text style={styles.metricValue}>
                  {onion.equivalent_diameter_mm !== null
                    ? `${onion.equivalent_diameter_mm.toFixed(1)} mm`
                    : 'Uncalibrated'}
                </Text>
              </View>
              {onion.major_axis_mm && (
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Ellipse Major / Minor:</Text>
                  <Text style={styles.metricValue}>
                    {onion.major_axis_mm.toFixed(1)} / {onion.minor_axis_mm?.toFixed(1)} mm
                  </Text>
                </View>
              )}
              {onion.mask_area_px && (
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Mask Area:</Text>
                  <Text style={styles.metricValue}>
                    {onion.mask_area_px.toLocaleString()} px
                  </Text>
                </View>
              )}
              {onion.explanation?.circularity && (
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Sphericity / Circularity:</Text>
                  <Text style={styles.metricValue}>
                    {onion.explanation.circularity} (Q-Factor)
                  </Text>
                </View>
              )}
              {onion.explanation?.surface_stain_pct && (
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Surface Stain Area:</Text>
                  <Text style={styles.metricValue}>
                    {onion.explanation.surface_stain_pct}
                  </Text>
                </View>
              )}
              {onion.explanation?.sunburn_pct && (
                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Sunburn (Green Shoulder):</Text>
                  <Text style={styles.metricValue}>
                    {onion.explanation.sunburn_pct}
                  </Text>
                </View>
              )}
              {onion.rejection_reasons && onion.rejection_reasons.includes('DOUBLE_BULB') && (
                <View style={styles.doubleBulbWarning}>
                  <Text style={styles.doubleBulbText}>
                    ⚠️ FUSED / SPLIT DOUBLE BULB: Deep contour concavity detected. Disqualified from Grade A.
                  </Text>
                </View>
              )}
              <Text style={styles.caveatText}>
                Note: Projected equivalent diameter from 2D top-down photograph.
                Not equivalent to laboratory caliper measurement.
              </Text>
            </View>

            {/* Defect Probability Breakdown */}
            <View style={styles.sectionCard}>
              <View style={styles.sectionHeaderRow}>
                <Text style={styles.sectionTitle}>Visible Surface Defects</Text>
                {onion.is_mock_defect && (
                  <Text style={styles.mockTag}>[DEMO MOCK]</Text>
                )}
              </View>

              <View style={styles.defectBarContainer}>
                <View style={styles.defectLabelRow}>
                  <Text style={styles.defectName}>Rotten / Decay:</Text>
                  <Text style={styles.defectPercent}>
                    {((onion.rotten_prob ?? 0) * 100).toFixed(0)}%
                  </Text>
                </View>
                <View style={styles.progressBar}>
                  <View
                    style={[
                      styles.progressFill,
                      {
                        width: `${Math.min(100, (onion.rotten_prob ?? 0) * 100)}%`,
                        backgroundColor:
                          (onion.rotten_prob ?? 0) >= 0.5 ? '#e74c3c' : '#2ecc71',
                      },
                    ]}
                  />
                </View>
              </View>

              <View style={styles.defectBarContainer}>
                <View style={styles.defectLabelRow}>
                  <Text style={styles.defectName}>Mechanical Damage:</Text>
                  <Text style={styles.defectPercent}>
                    {((onion.damaged_prob ?? 0) * 100).toFixed(0)}%
                  </Text>
                </View>
                <View style={styles.progressBar}>
                  <View
                    style={[
                      styles.progressFill,
                      {
                        width: `${Math.min(100, (onion.damaged_prob ?? 0) * 100)}%`,
                        backgroundColor:
                          (onion.damaged_prob ?? 0) >= 0.5 ? '#e67e22' : '#2ecc71',
                      },
                    ]}
                  />
                </View>
              </View>

              <View style={styles.defectBarContainer}>
                <View style={styles.defectLabelRow}>
                  <Text style={styles.defectName}>Vegetative Sprouting:</Text>
                  <Text style={styles.defectPercent}>
                    {((onion.sprouted_prob ?? 0) * 100).toFixed(0)}%
                  </Text>
                </View>
                <View style={styles.progressBar}>
                  <View
                    style={[
                      styles.progressFill,
                      {
                        width: `${Math.min(100, (onion.sprouted_prob ?? 0) * 100)}%`,
                        backgroundColor:
                          (onion.sprouted_prob ?? 0) >= 0.5 ? '#9b59b6' : '#2ecc71',
                      },
                    ]}
                  />
                </View>
              </View>

              {onion.has_human_correction && (
                <View style={styles.correctionNotice}>
                  <Text style={styles.correctionNoticeText}>
                    ✓ Corrected by: {onion.corrected_by || 'Officer'}
                  </Text>
                </View>
              )}
            </View>

            {/* Applied Policy & Explanation */}
            <View style={styles.sectionCard}>
              <Text style={styles.sectionTitle}>Applied Procurement Rule</Text>
              <Text style={styles.policyVersionText}>
                Active Policy: {onion.ruleset_version || 'DEMO_ASSUMPTION_v1'}
              </Text>
              {onion.rejection_reasons && onion.rejection_reasons.length > 0 && (
                <View style={styles.reasonsList}>
                  <Text style={styles.reasonsTitle}>Rejection Triggered By:</Text>
                  {onion.rejection_reasons.map((r, i) => (
                    <Text key={i} style={styles.reasonItem}>
                      • {r}
                    </Text>
                  ))}
                </View>
              )}
              {onion.explanation && Object.keys(onion.explanation).length > 0 && (
                <View style={styles.explanationBox}>
                  {Object.entries(onion.explanation).map(([k, v]) => (
                    <Text key={k} style={styles.explanationLine}>
                      <Text style={styles.explanationKey}>{k}: </Text>
                      {v}
                    </Text>
                  ))}
                </View>
              )}
            </View>

            {/* Officer Correction Section */}
            <View style={styles.sectionCard}>
              <Text style={styles.sectionTitle}>Officer Audit & Manual Override</Text>
              {!isCorrecting ? (
                <TouchableOpacity
                  style={styles.overrideBtn}
                  onPress={() => setIsCorrecting(true)}
                >
                  <Text style={styles.overrideBtnText}>
                    ✏️ Override / Correct AI Classification
                  </Text>
                </TouchableOpacity>
              ) : (
                <View style={styles.correctionForm}>
                  <Text style={styles.formHint}>
                    Adjust visual defect percentages if the AI made an error:
                  </Text>

                  <View style={styles.inputRow}>
                    <Text style={styles.inputLabel}>Damaged (%):</Text>
                    <TextInput
                      style={styles.numInput}
                      keyboardType="numeric"
                      value={damagedInput}
                      onChangeText={setDamagedInput}
                    />
                  </View>

                  <View style={styles.inputRow}>
                    <Text style={styles.inputLabel}>Rotten (%):</Text>
                    <TextInput
                      style={styles.numInput}
                      keyboardType="numeric"
                      value={rottenInput}
                      onChangeText={setRottenInput}
                    />
                  </View>

                  <View style={styles.inputRow}>
                    <Text style={styles.inputLabel}>Sprouted (%):</Text>
                    <TextInput
                      style={styles.numInput}
                      keyboardType="numeric"
                      value={sproutedInput}
                      onChangeText={setSproutedInput}
                    />
                  </View>

                  <TextInput
                    style={styles.remarksInput}
                    placeholder="Officer remarks (e.g. Visual skin cut verified)"
                    value={officerRemarks}
                    onChangeText={setOfficerRemarks}
                  />

                  <View style={styles.formBtnRow}>
                    <TouchableOpacity
                      style={styles.cancelBtn}
                      onPress={() => setIsCorrecting(false)}
                      disabled={saving}
                    >
                      <Text style={styles.cancelBtnText}>Cancel</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.saveBtn}
                      onPress={handleSaveCorrection}
                      disabled={saving}
                    >
                      {saving ? (
                        <ActivityIndicator color="#fff" size="small" />
                      ) : (
                        <Text style={styles.saveBtnText}>Save & Re-evaluate</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#0d1b2a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '90%',
    paddingBottom: 24,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  headerSubtitle: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  gradePill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  gradePillText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#fff',
  },
  closeButton: {
    padding: 6,
    backgroundColor: '#1e293b',
    borderRadius: 14,
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeButtonText: {
    color: '#cbd5e1',
    fontWeight: 'bold',
  },
  body: {
    flex: 1,
  },
  bodyContent: {
    padding: 16,
    gap: 12,
  },
  imageCard: {
    backgroundColor: '#1b263b',
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
  },
  toggleRow: {
    flexDirection: 'row',
    backgroundColor: '#0d1b2a',
    borderRadius: 8,
    padding: 3,
    marginBottom: 10,
  },
  toggleBtn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 6,
  },
  toggleBtnActive: {
    backgroundColor: '#415a77',
  },
  toggleBtnText: {
    fontSize: 11,
    color: '#94a3b8',
    fontWeight: '600',
  },
  toggleBtnTextActive: {
    color: '#fff',
    fontWeight: '700',
  },
  imageWrapper: {
    width: 220,
    height: 220,
    backgroundColor: '#000',
    borderRadius: 8,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  cropImage: {
    width: '100%',
    height: '100%',
  },
  noImage: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  noImageText: {
    color: '#64748b',
    fontSize: 12,
  },
  warningBox: {
    marginTop: 8,
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
    padding: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e74c3c',
  },
  warningText: {
    color: '#ff7675',
    fontSize: 11,
  },
  sectionCard: {
    backgroundColor: '#1b263b',
    borderRadius: 12,
    padding: 14,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#e2e8f0',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  mockTag: {
    fontSize: 9,
    color: '#ff7675',
    fontWeight: '700',
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#243347',
  },
  metricLabel: {
    fontSize: 12,
    color: '#94a3b8',
  },
  metricValue: {
    fontSize: 13,
    fontWeight: '700',
    color: '#f8f9fa',
  },
  caveatText: {
    fontSize: 10,
    color: '#64748b',
    marginTop: 8,
    fontStyle: 'italic',
  },
  defectBarContainer: {
    marginVertical: 4,
  },
  defectLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  defectName: {
    fontSize: 11,
    color: '#cbd5e1',
  },
  defectPercent: {
    fontSize: 11,
    fontWeight: '700',
    color: '#f8f9fa',
  },
  progressBar: {
    height: 6,
    backgroundColor: '#0d1b2a',
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  correctionNotice: {
    marginTop: 8,
    padding: 6,
    backgroundColor: 'rgba(46, 204, 113, 0.15)',
    borderRadius: 4,
  },
  correctionNoticeText: {
    color: '#2ecc71',
    fontSize: 11,
    fontWeight: '600',
  },
  policyVersionText: {
    fontSize: 11,
    color: '#38bdf8',
    marginBottom: 6,
  },
  reasonsList: {
    marginBottom: 6,
  },
  reasonsTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#f87171',
    marginBottom: 2,
  },
  reasonItem: {
    fontSize: 11,
    color: '#fca5a5',
    marginLeft: 6,
  },
  explanationBox: {
    backgroundColor: '#0d1b2a',
    padding: 8,
    borderRadius: 6,
    marginTop: 4,
  },
  explanationLine: {
    fontSize: 10,
    color: '#94a3b8',
    marginVertical: 1,
  },
  explanationKey: {
    fontWeight: '700',
    color: '#cbd5e1',
  },
  overrideBtn: {
    backgroundColor: '#2b3a4a',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 4,
  },
  overrideBtnText: {
    color: '#38bdf8',
    fontSize: 12,
    fontWeight: '700',
  },
  correctionForm: {
    marginTop: 8,
    gap: 8,
  },
  formHint: {
    fontSize: 11,
    color: '#94a3b8',
  },
  inputRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  inputLabel: {
    fontSize: 12,
    color: '#cbd5e1',
  },
  numInput: {
    backgroundColor: '#0d1b2a',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 6,
    width: 60,
    paddingHorizontal: 8,
    paddingVertical: 4,
    color: '#fff',
    fontSize: 12,
    textAlign: 'center',
  },
  remarksInput: {
    backgroundColor: '#0d1b2a',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    color: '#fff',
    fontSize: 11,
  },
  formBtnRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
    marginTop: 4,
  },
  cancelBtn: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#334155',
  },
  cancelBtnText: {
    color: '#cbd5e1',
    fontSize: 11,
  },
  saveBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#0284c7',
  },
  saveBtnText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  doubleBulbWarning: {
    marginTop: 8,
    padding: 8,
    backgroundColor: 'rgba(243, 156, 18, 0.18)',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#f39c12',
  },
  doubleBulbText: {
    color: '#f39c12',
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
  },
});
