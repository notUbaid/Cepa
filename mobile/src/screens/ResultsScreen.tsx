import React, { useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
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

  const handleOpenOnionDetail = async (onionSummary: OnionInstanceSummary) => {
    setLoadingDetail(true);
    try {
      const detail = await ApiClient.getOnionDetail(inspection.id, onionSummary.id);
      setSelectedOnion(detail);
      setModalVisible(true);
    } catch (err: any) {
      alert(`Could not load onion detail: ${err.message}`);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCorrectionSaved = (updated: OnionInstanceDetail) => {
    setSelectedOnion(updated);
    // Update local list
    setOnionsList((prev) =>
      prev.map((o) => (o.id === updated.id ? { ...o, ...updated } : o))
    );
  };

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      const finalized = await ApiClient.finalizeInspection(inspection.id);
      onFinalize(finalized);
    } catch (err: any) {
      alert(`Finalization failed: ${err.message}`);
    } finally {
      setFinalizing(false);
    }
  };

  const getGradePill = (grade: string | null) => {
    switch (grade) {
      case 'GRADE_A':
        return { bg: '#27ae60', text: 'GRADE A' };
      case 'URS':
        return { bg: '#f39c12', text: 'URS' };
      case 'REJECTED':
        return { bg: '#e74c3c', text: 'REJECTED' };
      default:
        return { bg: '#3498db', text: 'NEEDS REVIEW' };
    }
  };

  // Calculate local stats
  const total = onionsList.length;
  const gradeA = onionsList.filter((o) => o.grade === 'GRADE_A').length;
  const urs = onionsList.filter((o) => o.grade === 'URS').length;
  const rejected = onionsList.filter((o) => o.grade === 'REJECTED').length;
  const review = onionsList.filter((o) => o.grade === 'NEEDS_REVIEW' || !o.grade).length;

  const [viewMode, setViewMode] = useState<'grid' | 'overlay'>('grid');

  return (
    <View style={styles.container}>
      {/* Top Lot KPI Cards */}
      <View style={styles.kpiContainer}>
        <View style={[styles.kpiCard, { borderColor: '#27ae60' }]}>
          <Text style={styles.kpiValue}>{gradeA}</Text>
          <Text style={styles.kpiPercent}>
            {total ? `${((gradeA / total) * 100).toFixed(0)}%` : '0%'}
          </Text>
          <Text style={[styles.kpiLabel, { color: '#2ecc71' }]}>Grade A</Text>
        </View>

        <View style={[styles.kpiCard, { borderColor: '#f39c12' }]}>
          <Text style={styles.kpiValue}>{urs}</Text>
          <Text style={styles.kpiPercent}>
            {total ? `${((urs / total) * 100).toFixed(0)}%` : '0%'}
          </Text>
          <Text style={[styles.kpiLabel, { color: '#f39c12' }]}>URS</Text>
        </View>

        <View style={[styles.kpiCard, { borderColor: '#e74c3c' }]}>
          <Text style={styles.kpiValue}>{rejected}</Text>
          <Text style={styles.kpiPercent}>
            {total ? `${((rejected / total) * 100).toFixed(0)}%` : '0%'}
          </Text>
          <Text style={[styles.kpiLabel, { color: '#e74c3c' }]}>Rejected</Text>
        </View>

        <View style={[styles.kpiCard, { borderColor: '#3498db' }]}>
          <Text style={styles.kpiValue}>{review}</Text>
          <Text style={styles.kpiPercent}>
            {total ? `${((review / total) * 100).toFixed(0)}%` : '0%'}
          </Text>
          <Text style={[styles.kpiLabel, { color: '#38bdf8' }]}>Review</Text>
        </View>
      </View>

      {/* View Mode Switcher */}
      <View style={styles.viewModeToggleRow}>
        <TouchableOpacity
          style={[styles.viewModeBtn, viewMode === 'grid' && styles.viewModeBtnActive]}
          onPress={() => setViewMode('grid')}
        >
          <Text
            style={[
              styles.viewModeText,
              viewMode === 'grid' && styles.viewModeTextActive,
            ]}
          >
            📋 Interactive Grid
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.viewModeBtn, viewMode === 'overlay' && styles.viewModeBtnActive]}
          onPress={() => setViewMode('overlay')}
        >
          <Text
            style={[
              styles.viewModeText,
              viewMode === 'overlay' && styles.viewModeTextActive,
            ]}
          >
            🖼️ AI Detection Overlay
          </Text>
        </TouchableOpacity>
      </View>

      {viewMode === 'overlay' ? (
        <View style={styles.overlayViewContainer}>
          <View style={styles.overlayLegendRow}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#2ecc71' }]} />
              <Text style={styles.legendText}>Grade A</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#f39c12' }]} />
              <Text style={styles.legendText}>URS</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#e74c3c' }]} />
              <Text style={styles.legendText}>Rejected</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#3498db' }]} />
              <Text style={styles.legendText}>Review</Text>
            </View>
          </View>

          <View style={styles.overlayImageCard}>
            {sample.processed_image_url ? (
              <Image
                source={{ uri: sample.processed_image_url }}
                style={styles.annotatedFullImage}
                resizeMode="contain"
              />
            ) : sample.original_image_url ? (
              <Image
                source={{ uri: sample.original_image_url }}
                style={styles.annotatedFullImage}
                resizeMode="contain"
              />
            ) : (
              <View style={styles.noOverlayBox}>
                <Text style={styles.noOverlayText}>Annotated overlay not available</Text>
              </View>
            )}
          </View>
          <Text style={styles.overlayHint}>
            Pinch or zoom on device to inspect individual bulb segmentations and tags.
          </Text>
        </View>
      ) : (
        <>
          {/* Grid Header */}
          <View style={styles.gridHeaderRow}>
            <Text style={styles.gridTitle}>Detected Bulbs ({total})</Text>
            <Text style={styles.gridSub}>Tap any bulb to inspect evidence or override</Text>
          </View>

          {/* Onion Grid */}
          <FlatList
            data={onionsList}
            keyExtractor={(item) => item.id}
            numColumns={2}
            contentContainerStyle={styles.gridContent}
            columnWrapperStyle={styles.gridRow}
            renderItem={({ item }) => {
              const pill = getGradePill(item.grade);
          return (
            <TouchableOpacity
              style={styles.bulbCard}
              onPress={() => handleOpenOnionDetail(item)}
            >
              <View style={styles.bulbImgWrapper}>
                {item.crop_url ? (
                  <Image
                    source={{ uri: item.crop_url }}
                    style={styles.bulbImg}
                    resizeMode="contain"
                  />
                ) : (
                  <View style={styles.noBulbImg}>
                    <Text style={styles.noBulbText}>Bulb #{item.display_number}</Text>
                  </View>
                )}
                <View style={[styles.badgePill, { backgroundColor: pill.bg }]}>
                  <Text style={styles.badgeText}>{pill.text}</Text>
                </View>
              </View>

              <View style={styles.bulbInfo}>
                <View style={styles.bulbNameRow}>
                  <Text style={styles.bulbName}>Onion #{item.display_number}</Text>
                  <Text style={styles.tierTag}>{item.confidence_tier}</Text>
                </View>
                <Text style={styles.bulbSize}>
                  Size:{' '}
                  {item.equivalent_diameter_mm !== null
                    ? `${item.equivalent_diameter_mm.toFixed(1)} mm`
                    : 'N/A'}
                </Text>
              </View>
            </TouchableOpacity>
          );
        }}
      />
        </>
      )}

      {/* Bottom Sticky Action Bar */}
      <View style={styles.actionBar}>
        <TouchableOpacity
          style={styles.addSampleBtn}
          onPress={onAddSample}
          disabled={finalizing}
        >
          <Text style={styles.addSampleText}>+ Sample 2</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.finalizeBtn}
          onPress={handleFinalize}
          disabled={finalizing}
        >
          {finalizing ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <Text style={styles.finalizeBtnText}>Finalize & Generate Report →</Text>
          )}
        </TouchableOpacity>
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
    backgroundColor: '#0d1b2a',
    paddingHorizontal: 12,
    paddingTop: 12,
  },
  kpiContainer: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 12,
  },
  kpiCard: {
    flex: 1,
    backgroundColor: '#1b263b',
    borderRadius: 8,
    padding: 8,
    alignItems: 'center',
    borderWidth: 1,
  },
  kpiValue: {
    fontSize: 16,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  kpiPercent: {
    fontSize: 11,
    color: '#94a3b8',
    fontWeight: '600',
  },
  kpiLabel: {
    fontSize: 9,
    fontWeight: '800',
    textTransform: 'uppercase',
    marginTop: 2,
  },
  gridHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  gridTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  gridSub: {
    fontSize: 10,
    color: '#64748b',
  },
  gridContent: {
    paddingBottom: 85,
  },
  gridRow: {
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  bulbCard: {
    width: '48.5%',
    backgroundColor: '#1b263b',
    borderRadius: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#243347',
  },
  bulbImgWrapper: {
    width: '100%',
    height: 120,
    backgroundColor: '#000',
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  bulbImg: {
    width: '100%',
    height: '100%',
  },
  noBulbImg: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  noBulbText: {
    color: '#64748b',
    fontSize: 11,
  },
  badgePill: {
    position: 'absolute',
    top: 6,
    right: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeText: {
    color: '#fff',
    fontSize: 8,
    fontWeight: '800',
  },
  bulbInfo: {
    padding: 8,
  },
  bulbNameRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  bulbName: {
    fontSize: 12,
    fontWeight: '700',
    color: '#f8f9fa',
  },
  tierTag: {
    fontSize: 8,
    color: '#64748b',
    fontWeight: '600',
  },
  bulbSize: {
    fontSize: 11,
    color: '#38bdf8',
    fontWeight: '700',
    marginTop: 2,
  },
  actionBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#1b263b',
    padding: 12,
    flexDirection: 'row',
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: '#243347',
  },
  addSampleBtn: {
    flex: 1,
    backgroundColor: '#334155',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  addSampleText: {
    color: '#cbd5e1',
    fontSize: 12,
    fontWeight: '700',
  },
  finalizeBtn: {
    flex: 2.5,
    backgroundColor: '#0284c7',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  finalizeBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '800',
  },
  viewModeToggleRow: {
    flexDirection: 'row',
    backgroundColor: '#1b263b',
    borderRadius: 8,
    padding: 3,
    marginBottom: 10,
    gap: 4,
  },
  viewModeBtn: {
    flex: 1,
    paddingVertical: 7,
    alignItems: 'center',
    borderRadius: 6,
  },
  viewModeBtnActive: {
    backgroundColor: '#0284c7',
  },
  viewModeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#94a3b8',
  },
  viewModeTextActive: {
    color: '#fff',
  },
  overlayViewContainer: {
    flex: 1,
    paddingBottom: 75,
  },
  overlayLegendRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 16,
    marginBottom: 8,
    backgroundColor: '#1b263b',
    paddingVertical: 6,
    borderRadius: 6,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontSize: 10,
    color: '#cbd5e1',
    fontWeight: '600',
  },
  overlayImageCard: {
    flex: 1,
    minHeight: 320,
    backgroundColor: '#000',
    borderRadius: 10,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#334155',
    justifyContent: 'center',
    alignItems: 'center',
  },
  annotatedFullImage: {
    width: '100%',
    height: '100%',
  },
  noOverlayBox: {
    padding: 24,
    alignItems: 'center',
  },
  noOverlayText: {
    color: '#64748b',
    fontSize: 12,
  },
  overlayHint: {
    fontSize: 10,
    color: '#64748b',
    textAlign: 'center',
    marginTop: 6,
  },
});
