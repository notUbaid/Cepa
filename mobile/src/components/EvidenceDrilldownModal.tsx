import React, { useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { OnionInstanceDetail } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  GradeBadge,
  Haptics,
  LazyImage,
  Radius,
  SizeTierBadge,
  Spacing,
  Typography,
} from '../ui';

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
    Haptics.heavy();
    setSaving(true);
    try {
      const updated = await ApiClient.correctOnion(inspectionId, onion.id, {
        damaged_prob: Math.min(1.0, Math.max(0.0, parseFloat(damagedInput) / 100)),
        rotten_prob: Math.min(1.0, Math.max(0.0, parseFloat(rottenInput) / 100)),
        sprouted_prob: Math.min(1.0, Math.max(0.0, parseFloat(sproutedInput) / 100)),
        corrected_by: 'Procurement Officer',
        notes: officerRemarks || undefined,
      });
      Haptics.success();
      setIsCorrecting(false);
      onCorrectionSaved(updated);
    } catch (err: any) {
      Haptics.error();
      alert(`Correction failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true}>
      <View style={styles.overlay}>
        <View style={styles.modalCard}>
          {/* Swipe Indicator Handle */}
          <View style={styles.handleBar} />

          {/* Header */}
          <View style={styles.header}>
            <View>
              <View style={styles.headerTitleRow}>
                <Text style={styles.headerTitle}>Bulb #{onion.display_number}</Text>
                <SizeTierBadge tier={onion.mandi_size_grade} />
              </View>
              <Text style={styles.headerSubtitle}>
                Confidence: {(onion.segmentation_conf * 100).toFixed(0)}% • Tier:{' '}
                {onion.confidence_tier}
              </Text>
            </View>

            <View style={styles.headerRight}>
              <GradeBadge grade={onion.grade} size="md" />
              <AnimatedPressable
                haptic="light"
                onPress={onClose}
                style={styles.closeButton}
              >
                <Text style={styles.closeButtonText}>✕</Text>
              </AnimatedPressable>
            </View>
          </View>

          <ScrollView style={styles.body} contentContainerStyle={styles.bodyContent} showsVerticalScrollIndicator={false}>
            {/* Visual Evidence Toggle */}
            <FadeInView delay={50} distance={10}>
              <View style={styles.imageCard}>
                <View style={styles.toggleRow}>
                  <AnimatedPressable
                    haptic="selection"
                    style={[styles.toggleBtn, !showMask && styles.toggleBtnActive]}
                    onPress={() => setShowMask(false)}
                  >
                    <Text
                      style={[
                        styles.toggleBtnText,
                        !showMask && styles.toggleBtnTextActive,
                      ]}
                    >
                      Bulb Crop
                    </Text>
                  </AnimatedPressable>
                  <AnimatedPressable
                    haptic="selection"
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
                  </AnimatedPressable>
                </View>

                <View style={styles.imageWrapper}>
                  <LazyImage
                    source={{ uri: showMask ? onion.mask_url : onion.crop_url }}
                    style={styles.cropImage}
                    borderRadius={Radius.md}
                    resizeMode="contain"
                    fallbackText="🧅"
                  />
                </View>

                {onion.touches_border && (
                  <View style={styles.warningBox}>
                    <Text style={styles.warningText}>
                      ⚠️ Bulb touches image boundary. Caliper measurement may be truncated.
                    </Text>
                  </View>
                )}
              </View>
            </FadeInView>

            {/* Geometric Size Measurement */}
            <FadeInView delay={100} distance={12}>
              <View style={styles.sectionCard}>
                <Text style={styles.sectionTitle}>
                  MORPHOMETRY & PHYSICAL SIZING (BIS IS 17912:2022)
                </Text>

                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>APMC Mandi Grade:</Text>
                  <Text style={[styles.metricValue, { color: Colors.accent }]}>
                    {onion.mandi_size_grade || onion.explanation?.mandi_size_grade || 'Super'}
                  </Text>
                </View>

                <View style={styles.metricRow}>
                  <Text style={styles.metricLabel}>Equatorial Caliper (Deq):</Text>
                  <Text style={[styles.metricValue, { color: Colors.accent }]}>
                    {onion.equatorial_diameter_mm
                      ? `${onion.equatorial_diameter_mm.toFixed(1)} mm`
                      : onion.equivalent_diameter_mm !== null
                      ? `${onion.equivalent_diameter_mm.toFixed(1)} mm`
                      : 'Uncalibrated'}
                  </Text>
                </View>

                {(onion.polar_length_mm || onion.explanation?.polar_length_mm) && (
                  <View style={styles.metricRow}>
                    <Text style={styles.metricLabel}>Polar Axis (Stem-to-Root):</Text>
                    <Text style={styles.metricValue}>
                      {onion.polar_length_mm
                        ? `${onion.polar_length_mm.toFixed(1)} mm`
                        : onion.explanation?.polar_length_mm}
                    </Text>
                  </View>
                )}

                {(onion.shape_class || onion.explanation?.shape_class) && (
                  <View style={styles.metricRow}>
                    <Text style={styles.metricLabel}>Bulb Shape Classification:</Text>
                    <Text style={styles.metricValue}>
                      {onion.shape_class || onion.explanation?.shape_class}
                    </Text>
                  </View>
                )}

                {(onion.estimated_weight_grams || onion.explanation?.estimated_weight_grams) && (
                  <View style={styles.metricRow}>
                    <Text style={styles.metricLabel}>Volumetric Mass Estimate:</Text>
                    <Text style={[styles.metricValue, { color: Colors.gradeA }]}>
                      {onion.estimated_weight_grams
                        ? `${onion.estimated_weight_grams.toFixed(0)} g`
                        : onion.explanation?.estimated_weight_grams}
                    </Text>
                  </View>
                )}

                {onion.explanation?.black_mold_pct && (
                  <View style={styles.metricRow}>
                    <Text style={styles.metricLabel}>Black Mold (Aspergillus niger):</Text>
                    <Text style={[styles.metricValue, { color: Colors.reject }]}>
                      {onion.explanation.black_mold_pct}
                    </Text>
                  </View>
                )}

                {onion.explanation?.sunburn_pct && (
                  <View style={styles.metricRow}>
                    <Text style={styles.metricLabel}>Sunburn (Chlorophyll NGRDI):</Text>
                    <Text style={styles.metricValue}>
                      {onion.explanation.sunburn_pct}
                    </Text>
                  </View>
                )}

                {onion.explanation?.skin_baldness_pct && (
                  <View style={styles.metricRow}>
                    <Text style={styles.metricLabel}>Tunic Loss (Peeled Flesh):</Text>
                    <Text style={styles.metricValue}>
                      {onion.explanation.skin_baldness_pct}
                    </Text>
                  </View>
                )}

                {onion.rejection_reasons && onion.rejection_reasons.includes('DOUBLE_BULB') && (
                  <View style={styles.doubleBulbWarning}>
                    <Text style={styles.doubleBulbText}>
                      ⚠️ TWIN / DOUBLE BULB: Deep contour concavity detected. Disqualified from Grade A.
                    </Text>
                  </View>
                )}
              </View>
            </FadeInView>

            {/* Defect Probability Breakdown */}
            <FadeInView delay={150} distance={12}>
              <View style={styles.sectionCard}>
                <View style={styles.sectionHeaderRow}>
                  <Text style={styles.sectionTitle}>MULTI-SPECTRAL DEFECT ANALYSIS</Text>
                  {onion.is_mock_defect && (
                    <Text style={styles.mockTag}>[DEMO MOCK]</Text>
                  )}
                </View>

                <DefectBar
                  label="Rotten / Fungal Decay"
                  percent={((onion.rotten_prob ?? 0) * 100).toFixed(0)}
                  color={Colors.reject}
                />
                <DefectBar
                  label="Mechanical Impact / Damage"
                  percent={((onion.damaged_prob ?? 0) * 100).toFixed(0)}
                  color={Colors.urs}
                />
                <DefectBar
                  label="Vegetative Sprouting"
                  percent={((onion.sprouted_prob ?? 0) * 100).toFixed(0)}
                  color={Colors.review}
                />

                {onion.has_human_correction && (
                  <View style={styles.correctionNotice}>
                    <Text style={styles.correctionNoticeText}>
                      ✓ Verified & Adjusted by: {onion.corrected_by || 'Procurement Officer'}
                    </Text>
                  </View>
                )}
              </View>
            </FadeInView>

            {/* Applied Policy & Reasons */}
            <FadeInView delay={200} distance={12}>
              <View style={styles.sectionCard}>
                <Text style={styles.sectionTitle}>MANDI RULE ENGINE AUDIT</Text>
                <Text style={styles.policyVersionText}>
                  Rule Standard: {onion.ruleset_version || 'BIS_IS_17912_2022'}
                </Text>

                {onion.rejection_reasons && onion.rejection_reasons.length > 0 && (
                  <View style={styles.reasonsList}>
                    <Text style={styles.reasonsTitle}>Rejection Triggered By:</Text>
                    {onion.rejection_reasons.map((r, i) => (
                      <Text key={i} style={styles.reasonItem}>
                        • {r.replace(/_/g, ' ')}
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
            </FadeInView>

            {/* Officer Manual Override */}
            <FadeInView delay={250} distance={12}>
              <View style={styles.sectionCard}>
                <Text style={styles.sectionTitle}>OFFICER AUDIT & MANUAL OVERRIDE</Text>
                {!isCorrecting ? (
                  <AnimatedPressable
                    haptic="medium"
                    style={styles.overrideBtn}
                    onPress={() => setIsCorrecting(true)}
                  >
                    <Text style={styles.overrideBtnText}>
                      ✏️ Override / Correct AI Classification
                    </Text>
                  </AnimatedPressable>
                ) : (
                  <View style={styles.correctionForm}>
                    <Text style={styles.formHint}>
                      Input calibrated defect percentages to override AI appraisal:
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
                      placeholder="Officer audit remarks (e.g. Visual rot confirmed on root plate)"
                      placeholderTextColor={Colors.textDim}
                      value={officerRemarks}
                      onChangeText={setOfficerRemarks}
                    />

                    <View style={styles.formBtnRow}>
                      <AnimatedPressable
                        haptic="light"
                        style={styles.cancelBtn}
                        onPress={() => setIsCorrecting(false)}
                        disabled={saving}
                      >
                        <Text style={styles.cancelBtnText}>Cancel</Text>
                      </AnimatedPressable>

                      <AnimatedPressable
                        haptic="heavy"
                        style={styles.saveBtn}
                        onPress={handleSaveCorrection}
                        disabled={saving}
                      >
                        {saving ? (
                          <ActivityIndicator color={Colors.text} size="small" />
                        ) : (
                          <Text style={styles.saveBtnText}>Save & Re-evaluate</Text>
                        )}
                      </AnimatedPressable>
                    </View>
                  </View>
                )}
              </View>
            </FadeInView>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

const DefectBar: React.FC<{ label: string; percent: string; color: string }> = ({
  label,
  percent,
  color,
}) => {
  const pct = Math.min(100, Math.max(0, parseFloat(percent) || 0));
  return (
    <View style={styles.defectBarContainer}>
      <View style={styles.defectLabelRow}>
        <Text style={styles.defectName}>{label}</Text>
        <Text style={[styles.defectPercent, { color }]}>{percent}%</Text>
      </View>
      <View style={styles.progressBar}>
        <View
          style={[
            styles.progressFill,
            {
              width: `${pct}%`,
              backgroundColor: pct >= 30 ? color : Colors.gradeA,
            },
          ]}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(7, 13, 24, 0.85)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: Colors.bg,
    borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl,
    maxHeight: '92%',
    paddingBottom: Spacing.xl,
    borderTopWidth: 1,
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: Colors.border,
  },
  handleBar: {
    width: 38,
    height: 4,
    borderRadius: 2,
    backgroundColor: Colors.borderMuted,
    alignSelf: 'center',
    marginTop: 10,
    marginBottom: 4,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderMuted,
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerTitle: {
    ...Typography.title1,
    color: Colors.text,
  },
  headerSubtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 2,
    fontFamily: 'monospace',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.cardBgElevated,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  closeButtonText: {
    color: Colors.textMuted,
    fontWeight: 'bold',
    fontSize: 13,
  },
  body: {
    flex: 1,
  },
  bodyContent: {
    padding: Spacing.lg,
    gap: Spacing.md,
  },
  imageCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  toggleRow: {
    flexDirection: 'row',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.sm,
    padding: 3,
    marginBottom: Spacing.sm,
  },
  toggleBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 5,
    borderRadius: Radius.xs,
  },
  toggleBtnActive: {
    backgroundColor: Colors.accentSubtle,
    borderWidth: 1,
    borderColor: Colors.accent,
  },
  toggleBtnText: {
    fontSize: 11,
    color: Colors.textDim,
    fontWeight: '600',
  },
  toggleBtnTextActive: {
    color: Colors.accent,
    fontWeight: '700',
  },
  imageWrapper: {
    width: 200,
    height: 200,
    borderRadius: Radius.md,
    overflow: 'hidden',
    backgroundColor: Colors.skeletonBase,
  },
  cropImage: {
    width: '100%',
    height: '100%',
  },
  warningBox: {
    marginTop: Spacing.sm,
    backgroundColor: Colors.rejectBg,
    padding: Spacing.sm,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
    width: '100%',
  },
  warningText: {
    color: Colors.reject,
    fontSize: 11,
    textAlign: 'center',
  },
  sectionCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.xs,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.accent,
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  mockTag: {
    fontSize: 9,
    color: Colors.reject,
    fontWeight: '700',
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderMuted,
  },
  metricLabel: {
    fontSize: 12,
    color: Colors.textMuted,
  },
  metricValue: {
    fontSize: 12,
    fontWeight: '700',
    color: Colors.text,
    fontFamily: 'monospace',
  },
  doubleBulbWarning: {
    marginTop: Spacing.sm,
    padding: Spacing.sm,
    backgroundColor: Colors.ursBg,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: Colors.urs,
  },
  doubleBulbText: {
    color: Colors.urs,
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 16,
  },
  defectBarContainer: {
    marginVertical: 4,
  },
  defectLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 3,
  },
  defectName: {
    fontSize: 11,
    color: Colors.textSecondary,
  },
  defectPercent: {
    fontSize: 11,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  progressBar: {
    height: 6,
    backgroundColor: Colors.cardBgElevated,
    borderRadius: 3,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  correctionNotice: {
    marginTop: Spacing.sm,
    padding: Spacing.sm,
    backgroundColor: Colors.gradeABg,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
  },
  correctionNoticeText: {
    color: Colors.gradeA,
    fontSize: 11,
    fontWeight: '600',
  },
  policyVersionText: {
    fontSize: 11,
    color: Colors.textDim,
    fontFamily: 'monospace',
    marginBottom: 6,
  },
  reasonsList: {
    marginBottom: 6,
    backgroundColor: Colors.rejectBg,
    padding: Spacing.sm,
    borderRadius: Radius.sm,
  },
  reasonsTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.reject,
    marginBottom: 2,
  },
  reasonItem: {
    fontSize: 11,
    color: '#fca5a5',
    marginLeft: 4,
    fontFamily: 'monospace',
  },
  explanationBox: {
    backgroundColor: Colors.cardBgElevated,
    padding: Spacing.sm,
    borderRadius: Radius.sm,
    marginTop: 4,
  },
  explanationLine: {
    fontSize: 10,
    color: Colors.textMuted,
    marginVertical: 1,
    fontFamily: 'monospace',
  },
  explanationKey: {
    fontWeight: '700',
    color: Colors.accent,
  },
  overrideBtn: {
    backgroundColor: Colors.cardBgElevated,
    padding: Spacing.md,
    borderRadius: Radius.md,
    alignItems: 'center',
    marginTop: Spacing.xs,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  overrideBtnText: {
    color: Colors.accent,
    fontSize: 12,
    fontWeight: '700',
  },
  correctionForm: {
    marginTop: Spacing.sm,
    gap: Spacing.sm,
  },
  formHint: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  inputRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  inputLabel: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  numInput: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    borderRadius: Radius.sm,
    width: 65,
    paddingHorizontal: 8,
    paddingVertical: 4,
    color: Colors.text,
    fontSize: 12,
    textAlign: 'center',
    fontFamily: 'monospace',
  },
  remarksInput: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: 8,
    color: Colors.text,
    fontSize: 11,
  },
  formBtnRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: Spacing.sm,
    marginTop: Spacing.xs,
  },
  cancelBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 8,
    borderRadius: Radius.sm,
    backgroundColor: Colors.cardBgElevated,
  },
  cancelBtnText: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
  },
  saveBtn: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: 8,
    borderRadius: Radius.sm,
    backgroundColor: Colors.accentDark,
  },
  saveBtnText: {
    color: Colors.text,
    fontSize: 11,
    fontWeight: '800',
  },
});
