import React, { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { EvidenceDrilldownModal } from '../components/EvidenceDrilldownModal';
import {
  InspectionDetail,
  OnionInstanceDetail,
  OnionInstanceSummary,
  SampleDetail,
} from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  GradeBadge,
  Haptics,
  LazyImage,
  Radius,
  Shadows,
  SizeTierBadge,
  SkeletonKpiCard,
  SkeletonOnionCard,
  Spacing,
  Typography,
} from '../ui';

interface ResultsScreenProps {
  inspection: InspectionDetail;
  sample: SampleDetail;
  onFinalize: (finalizedInspection: InspectionDetail) => void;
  onAddSample: () => void;
}

export const ResultsScreen: React.FC<ResultsScreenProps> = ({
  inspection,
  sample,
  onFinalize,
  onAddSample,
}) => {
  const [selectedOnion, setSelectedOnion] = useState<OnionInstanceDetail | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [onionsList, setOnionsList] = useState<OnionInstanceSummary[]>(
    sample.onion_instances || []
  );

  const [viewMode, setViewMode] = useState<'grid' | 'overlay'>('grid');
  const [gradeFilter, setGradeFilter] = useState<'ALL' | 'GRADE_A' | 'URS' | 'REJECTED'>('ALL');

  const handleOpenOnionDetail = async (onionSummary: OnionInstanceSummary) => {
    Haptics.medium();
    setLoadingDetail(true);
    try {
      const detail = await ApiClient.getOnionDetail(inspection.id, onionSummary.id);
      setSelectedOnion(detail);
      setModalVisible(true);
    } catch (err: any) {
      Haptics.error();
      alert(`Could not load onion detail: ${err.message}`);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCorrectionSaved = (updated: OnionInstanceDetail) => {
    setSelectedOnion(updated);
    setOnionsList((prev) =>
      prev.map((o) => (o.id === updated.id ? { ...o, ...updated } : o))
    );
  };

  const handleFinalize = async () => {
    Haptics.heavy();
    setFinalizing(true);
    try {
      const finalized = await ApiClient.finalizeInspection(inspection.id);
      Haptics.success();
      onFinalize(finalized);
    } catch (err: any) {
      Haptics.error();
      alert(`Finalization failed: ${err.message}`);
    } finally {
      setFinalizing(false);
    }
  };

  // KPI Calculations
  const total = onionsList.length;
  const gradeA = onionsList.filter((o) => o.grade === 'GRADE_A').length;
  const urs = onionsList.filter((o) => o.grade === 'URS').length;
  const rejected = onionsList.filter((o) => o.grade === 'REJECTED').length;
  const review = onionsList.filter((o) => o.grade === 'NEEDS_REVIEW' || !o.grade).length;

  const filteredOnions = onionsList.filter((o) => {
    if (gradeFilter === 'GRADE_A') return o.grade === 'GRADE_A';
    if (gradeFilter === 'URS') return o.grade === 'URS';
    if (gradeFilter === 'REJECTED') return o.grade === 'REJECTED';
    return true;
  });

  return (
    <View style={styles.container}>
      {/* Top Lot KPI Cards */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.kpiContainer}>
          <AnimatedPressable
            haptic="selection"
            onPress={() => setGradeFilter(gradeFilter === 'GRADE_A' ? 'ALL' : 'GRADE_A')}
            style={[
              styles.kpiCard,
              gradeFilter === 'GRADE_A' && styles.kpiCardSelected,
            ]}
          >
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.gradeA }]} />
              <Text style={styles.kpiValue}>{gradeA}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((gradeA / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>Grade A</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            onPress={() => setGradeFilter(gradeFilter === 'URS' ? 'ALL' : 'URS')}
            style={[
              styles.kpiCard,
              gradeFilter === 'URS' && styles.kpiCardSelected,
            ]}
          >
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.urs }]} />
              <Text style={styles.kpiValue}>{urs}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((urs / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>URS</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            onPress={() => setGradeFilter(gradeFilter === 'REJECTED' ? 'ALL' : 'REJECTED')}
            style={[
              styles.kpiCard,
              gradeFilter === 'REJECTED' && styles.kpiCardSelected,
            ]}
          >
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.reject }]} />
              <Text style={styles.kpiValue}>{rejected}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((rejected / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>Reject</Text>
          </AnimatedPressable>

          <View style={styles.kpiCard}>
            <View style={styles.kpiDotRow}>
              <View style={[styles.kpiDot, { backgroundColor: Colors.review }]} />
              <Text style={styles.kpiValue}>{review}</Text>
            </View>
            <Text style={styles.kpiPercent}>
              {total ? `${((review / total) * 100).toFixed(0)}%` : '0%'}
            </Text>
            <Text style={styles.kpiLabel}>Review</Text>
          </View>
        </View>
      </FadeInView>

      {/* View Mode Switcher */}
      <FadeInView delay={100} distance={10}>
        <View style={styles.viewModeToggleRow}>
          <AnimatedPressable
            haptic="selection"
            style={[styles.viewModeBtn, viewMode === 'grid' && styles.viewModeBtnActive]}
            onPress={() => setViewMode('grid')}
          >
            <Text
              style={[
                styles.viewModeText,
                viewMode === 'grid' && styles.viewModeTextActive,
              ]}
            >
              Bulb Grid ({filteredOnions.length})
            </Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="selection"
            style={[styles.viewModeBtn, viewMode === 'overlay' && styles.viewModeBtnActive]}
            onPress={() => setViewMode('overlay')}
          >
            <Text
              style={[
                styles.viewModeText,
                viewMode === 'overlay' && styles.viewModeTextActive,
              ]}
            >
              Annotated View
            </Text>
          </AnimatedPressable>
        </View>
      </FadeInView>

      {/* Main View Area */}
      {viewMode === 'overlay' ? (
        <FadeInView delay={150} distance={12} style={styles.overlayViewContainer}>
          <View style={styles.overlayLegendRow}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.gradeA }]} />
              <Text style={styles.legendText}>Grade A</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.urs }]} />
              <Text style={styles.legendText}>URS</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.reject }]} />
              <Text style={styles.legendText}>Reject</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: Colors.accent }]} />
              <Text style={styles.legendText}>Caliper Bar</Text>
            </View>
          </View>

          <View style={styles.overlayImageCard}>
            <LazyImage
              source={{
                uri: sample.processed_image_url || sample.original_image_url,
              }}
              style={styles.annotatedFullImage}
              resizeMode="contain"
            />
          </View>
          <Text style={styles.overlayHint}>
            Cyan = Equatorial Diameter (Deq) • Magenta = Polar Length
          </Text>
        </FadeInView>
      ) : (
        <View style={styles.gridContainer}>
          {/* Quick Filter Bar */}
          {gradeFilter !== 'ALL' && (
            <View style={styles.activeFilterBanner}>
              <Text style={styles.activeFilterText}>
                Showing {gradeFilter.replace('_', ' ')} only ({filteredOnions.length})
              </Text>
              <AnimatedPressable
                haptic="selection"
                onPress={() => setGradeFilter('ALL')}
                style={styles.clearFilterBtn}
              >
                <Text style={styles.clearFilterText}>Reset ✕</Text>
              </AnimatedPressable>
            </View>
          )}

          {/* Onion Grid */}
          <FlatList
            data={filteredOnions}
            keyExtractor={(item) => item.id}
            numColumns={2}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.gridContent}
            columnWrapperStyle={styles.gridRow}
            renderItem={({ item, index }) => (
              <FadeInView delay={Math.min(index * 40, 240)} distance={8} style={styles.bulbCardWrapper}>
                <AnimatedPressable
                  haptic="medium"
                  style={styles.bulbCard}
                  onPress={() => handleOpenOnionDetail(item)}
                >
                  <View style={styles.bulbImgWrapper}>
                    <LazyImage
                      source={{ uri: item.crop_url }}
                      style={styles.bulbImg}
                      borderRadius={Radius.md}
                      resizeMode="contain"
                    />
                    <View style={styles.badgePillContainer}>
                      <GradeBadge grade={item.grade} size="sm" />
                    </View>
                  </View>

                  <View style={styles.bulbInfo}>
                    <View style={styles.bulbNameRow}>
                      <Text style={styles.bulbName}>#{item.display_number}</Text>
                      <SizeTierBadge tier={item.mandi_size_grade} />
                    </View>

                    <View style={styles.telemetryRow}>
                      <Text style={styles.diaText}>
                        {item.equatorial_diameter_mm !== null && item.equatorial_diameter_mm !== undefined
                          ? `Ø ${item.equatorial_diameter_mm.toFixed(1)}mm`
                          : item.equivalent_diameter_mm !== null
                          ? `Ø ${item.equivalent_diameter_mm.toFixed(1)}mm`
                          : 'Ø N/A'}
                      </Text>
                      {item.estimated_weight_grams !== undefined && item.estimated_weight_grams !== null && (
                        <Text style={styles.weightText}>
                          {item.estimated_weight_grams.toFixed(0)}g
                        </Text>
                      )}
                    </View>

                    {/* Defect Warning Chip */}
                    {(item.sprouted_prob ?? 0) > 0.3 ||
                    (item.rotten_prob ?? 0) > 0.3 ||
                    (item.damaged_prob ?? 0) > 0.3 ? (
                      <View style={styles.defectAlertPill}>
                        <Text style={styles.defectAlertText}>
                          {(item.rotten_prob ?? 0) > 0.3
                            ? 'Rotten'
                            : (item.sprouted_prob ?? 0) > 0.3
                            ? 'Sprouted'
                            : 'Damaged'}
                        </Text>
                      </View>
                    ) : null}
                  </View>
                </AnimatedPressable>
              </FadeInView>
            )}
          />
        </View>
      )}

      {/* Bottom Sticky Action Bar */}
      <View style={styles.actionBar}>
        <AnimatedPressable
          haptic="light"
          style={styles.addSampleBtn}
          onPress={onAddSample}
          disabled={finalizing}
        >
          <Text style={styles.addSampleText}>+ Sample 2</Text>
        </AnimatedPressable>

        <AnimatedPressable
          haptic="heavy"
          style={styles.finalizeBtn}
          onPress={handleFinalize}
          disabled={finalizing}
        >
          {finalizing ? (
            <ActivityIndicator color="#ffffff" size="small" />
          ) : (
            <Text style={styles.finalizeBtnText}>Finalize & Certify Lot →</Text>
          )}
        </AnimatedPressable>
      </View>

      {/* Evidence Drilldown Modal */}
      <EvidenceDrilldownModal
        visible={modalVisible}
        onion={selectedOnion}
        inspectionId={inspection.id}
        onClose={() => setModalVisible(false)}
        onCorrectionSaved={handleCorrectionSaved}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.sm,
  },
  kpiContainer: {
    flexDirection: 'row',
    gap: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  kpiCard: {
    flex: 1,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.md,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xs,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  kpiCardSelected: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1.5,
    borderColor: Colors.accent,
  },
  kpiDotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  kpiDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  kpiValue: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text,
  },
  kpiPercent: {
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 1,
  },
  kpiLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginTop: 1,
  },
  viewModeToggleRow: {
    flexDirection: 'row',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    padding: 3,
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  viewModeBtn: {
    flex: 1,
    paddingVertical: 7,
    alignItems: 'center',
    borderRadius: Radius.sm,
  },
  viewModeBtnActive: {
    backgroundColor: Colors.accent,
  },
  viewModeText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  viewModeTextActive: {
    color: '#ffffff',
    fontWeight: '600',
  },
  gridContainer: {
    flex: 1,
  },
  activeFilterBanner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.sm,
    marginBottom: Spacing.xs,
  },
  activeFilterText: {
    fontSize: 11,
    color: Colors.accent,
    fontWeight: '600',
  },
  clearFilterBtn: {
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  clearFilterText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontWeight: '700',
  },
  gridContent: {
    paddingBottom: 85,
  },
  gridRow: {
    justifyContent: 'space-between',
    marginBottom: Spacing.sm,
  },
  bulbCardWrapper: {
    width: '48.5%',
  },
  bulbCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  bulbImgWrapper: {
    width: '100%',
    height: 115,
    backgroundColor: Colors.skeletonBase,
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bulbImg: {
    width: '100%',
    height: '100%',
  },
  badgePillContainer: {
    position: 'absolute',
    top: 6,
    right: 6,
  },
  bulbInfo: {
    padding: Spacing.sm,
  },
  bulbNameRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  bulbName: {
    fontSize: 13,
    fontWeight: '800',
    color: Colors.text,
  },
  telemetryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  diaText: {
    fontSize: 12,
    color: Colors.accent,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  weightText: {
    fontSize: 11,
    color: Colors.textMuted,
    fontFamily: 'monospace',
  },
  defectAlertPill: {
    backgroundColor: Colors.rejectBg,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radius.xs,
    marginTop: 5,
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
  },
  defectAlertText: {
    fontSize: 9,
    fontWeight: '800',
    color: Colors.reject,
  },
  overlayViewContainer: {
    flex: 1,
    paddingBottom: 85,
  },
  overlayLegendRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: Spacing.md,
    marginBottom: Spacing.sm,
    backgroundColor: Colors.cardBg,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  legendDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  legendText: {
    fontSize: 10,
    color: Colors.textMuted,
    fontWeight: '600',
  },
  overlayImageCard: {
    flex: 1,
    minHeight: 320,
    backgroundColor: '#000',
    borderRadius: Radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  annotatedFullImage: {
    width: '100%',
    height: '100%',
  },
  overlayHint: {
    fontSize: 11,
    color: Colors.textDim,
    textAlign: 'center',
    marginTop: 6,
    fontFamily: 'monospace',
  },
  actionBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: Colors.cardBg,
    padding: Spacing.md,
    flexDirection: 'row',
    gap: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    ...Shadows.modal,
  },
  addSampleBtn: {
    flex: 1,
    backgroundColor: Colors.cardBgElevated,
    paddingVertical: 13,
    borderRadius: Radius.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  addSampleText: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  finalizeBtn: {
    flex: 2.4,
    backgroundColor: Colors.accent,
    paddingVertical: 13,
    borderRadius: Radius.md,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.accent,
    ...Shadows.card,
  },
  finalizeBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
});
