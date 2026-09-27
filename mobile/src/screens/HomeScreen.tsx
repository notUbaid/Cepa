import React, { useEffect, useState } from 'react';
import {
  FlatList,
  Image,
  Platform,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { InspectionSummary } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  GradeBadge,
  Haptics,
  Radius,
  Shadows,
  SkeletonInspectionRow,
  SkeletonKpiCard,
  Spacing,
  Typography,
} from '../ui';

interface HomeScreenProps {
  onStartNewInspection: (mode?: 'CAMERA' | 'UPLOAD') => void;
  onSelectInspection: (id: string) => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onStartNewInspection,
  onSelectInspection,
}) => {
  const [inspections, setInspections] = useState<InspectionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<'ALL' | 'FINALIZED' | 'REVIEW'>('ALL');
  const [loadingDemoLot, setLoadingDemoLot] = useState(false);

  const handleLoadDemoLot = async () => {
    Haptics.heavy();
    setLoadingDemoLot(true);
    try {
      const list = await ApiClient.listInspections();
      const existing = list.find((i) => (i.lot_id || '').includes('DEMO') && i.sample_count > 0);
      if (existing) {
        onSelectInspection(existing.id);
        return;
      }

      const insp = await ApiClient.createInspection({
        lot_id: 'MANDI-DEMO-VERIFIED-01',
        procurement_centre: 'Lasalgaon APMC Yard, Nashik',
        officer_name: 'Senior Grader S. Patil',
        officer_id: 'NAFED-MH-084',
        notes: 'Verified real mandi onion sample with 24 bulbs & ChArUco 7x5 card',
      });
      const demoUrl = ApiClient.getDemoSampleUrl();
      await ApiClient.uploadSample(insp.id, demoUrl);
      onSelectInspection(insp.id);
    } catch (e: any) {
      alert(`Could not load demo lot: ${e.message}`);
    } finally {
      setLoadingDemoLot(false);
    }
  };

  const loadData = async () => {
    try {
      const list = await ApiClient.listInspections().catch(() => []);
      setInspections(list);
    } catch (e) {
      console.warn('Failed to load home data', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    Haptics.light();
    setRefreshing(true);
    loadData();
  };

  const filteredInspections = inspections.filter((item) => {
    if (filter === 'FINALIZED') return item.status === 'FINALIZED';
    if (filter === 'REVIEW') return item.status === 'REVIEW' || item.status === 'DRAFT';
    return true;
  });

  const totalLots = inspections.length;
  const finalizedLots = inspections.filter((i) => i.status === 'FINALIZED').length;
  const inReviewLots = inspections.filter((i) => i.status !== 'FINALIZED').length;

  return (
    <View style={styles.container}>
      {/* Executive Mandi Telemetry Bento Bar */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.kpiRow}>
          {loading ? (
            <>
              <SkeletonKpiCard />
              <SkeletonKpiCard />
              <SkeletonKpiCard />
            </>
          ) : (
            <>
              <View style={[styles.kpiCard, styles.kpiCardSlate]}>
                <View style={styles.kpiHeaderRow}>
                  <Text style={styles.kpiPillTag}>CONSIGNMENTS</Text>
                </View>
                <Text style={styles.kpiValue}>{totalLots}</Text>
                <Text style={styles.kpiSubLabel}>Recorded Lots</Text>
              </View>

              <View style={[styles.kpiCard, styles.kpiCardEmerald]}>
                <View style={styles.kpiHeaderRow}>
                  <View style={styles.liveEmeraldDot} />
                  <Text style={[styles.kpiPillTag, { color: '#047857' }]}>GRADE A</Text>
                </View>
                <Text style={[styles.kpiValue, { color: '#047857' }]}>{finalizedLots}</Text>
                <Text style={styles.kpiSubLabel}>
                  {totalLots > 0 ? `${Math.round((finalizedLots / totalLots) * 100)}% Certified` : '0% Certified'}
                </Text>
              </View>

              <View style={[styles.kpiCard, styles.kpiCardCyan]}>
                <View style={styles.kpiHeaderRow}>
                  <Text style={[styles.kpiPillTag, { color: '#0284c7' }]}>CALIPER LOCK</Text>
                </View>
                <Text style={[styles.kpiValue, { color: '#0369a1' }]}>
                  ±0.5<Text style={styles.kpiUnit}>mm</Text>
                </Text>
                <Text style={styles.kpiSubLabel}>ChArUco 7×5</Text>
              </View>
            </>
          )}
        </View>
      </FadeInView>

      {/* Optical Station Setup Visual Banner */}
      <FadeInView delay={80} distance={10}>
        <View style={styles.stationBanner}>
          <Image
            source={require('../../assets/calibration_guide.png')}
            style={styles.stationImage}
            resizeMode="cover"
          />
          <View style={styles.stationOverlay}>
            <View style={styles.stationBadgeRow}>
              <View style={styles.stationBadge}>
                <Text style={styles.stationBadgeText}>APMC OPTICAL BENCH</Text>
              </View>
              <View style={styles.stationPillSecondary}>
                <Text style={styles.stationPillSecondaryText}>70CM RIG</Text>
              </View>
            </View>
            <Text style={styles.stationTitle}>Precision Overhead Scanner</Text>
            <Text style={styles.stationDesc}>
              Single-layer spread with 40mm ChArUco 7×5 marker for sub-millimeter caliber grading.
            </Text>
            <View style={styles.stationChipRow}>
              <View style={styles.stationChip}>
                <Text style={styles.stationChipText}>✓ 40mm Marker</Text>
              </View>
              <View style={styles.stationChip}>
                <Text style={styles.stationChipText}>✓ YOLO11-seg</Text>
              </View>
              <View style={styles.stationChip}>
                <Text style={styles.stationChipText}>✓ NAFED MSP</Text>
              </View>
            </View>
          </View>
        </View>
      </FadeInView>

      {/* Action Center */}
      <FadeInView delay={110} distance={12}>
        {/* Primary Action Button: Live Optical Scanner */}
        <AnimatedPressable
          haptic="heavy"
          onPress={() => onStartNewInspection('CAMERA')}
          style={styles.heroActionCard}
        >
          <View style={styles.heroContent}>
            <View style={styles.heroAperturePod}>
              <Text style={styles.heroApertureIcon}>📷</Text>
            </View>
            <View style={styles.heroTextContainer}>
              <View style={styles.heroMicroPill}>
                <View style={styles.heroDotLive} />
                <Text style={styles.heroMicroPillText}>LIVE APMC CALIPER SCANNER</Text>
              </View>
              <Text style={styles.heroTitle}>Start New Lot Inspection</Text>
              <Text style={styles.heroSubtitle}>
                Calibrate optical marker, scan bulb spread &amp; grade MSP dockage
              </Text>
            </View>
            <View style={styles.heroChevronBadge}>
              <Text style={styles.heroChevron}>Scan →</Text>
            </View>
          </View>
        </AnimatedPressable>

        {/* Dual Rapid-Access Action Row */}
        <View style={styles.rapidActionRow}>
          {/* Upload Photo Option */}
          <AnimatedPressable
            haptic="medium"
            onPress={() => onStartNewInspection('UPLOAD')}
            style={styles.rapidCard}
          >
            <View style={styles.rapidIconPod}>
              <Text style={styles.rapidIcon}>↑</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rapidTitle}>Upload Photo File</Text>
              <Text style={styles.rapidSubtitle}>
                Select image from laptop / library
              </Text>
            </View>
            <View style={styles.rapidTag}>
              <Text style={styles.rapidTagText}>IMAGE FILE</Text>
            </View>
          </AnimatedPressable>

          {/* 1-Tap Real Mandi Demo Lot Button */}
          <AnimatedPressable
            haptic="heavy"
            onPress={handleLoadDemoLot}
            style={[styles.rapidCard, styles.rapidCardDemo]}
            disabled={loadingDemoLot}
          >
            <View style={[styles.rapidIconPod, styles.rapidIconPodAmber]}>
              <Text style={styles.rapidIconAmber}>◈</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rapidTitle}>Mandi Demo Lot</Text>
              <Text style={styles.rapidSubtitle}>
                24 real bulbs · ChArUco 7×5
              </Text>
            </View>
            <View style={styles.demoLotBadge}>
              <Text style={styles.demoLotBadgeText}>24 BULBS</Text>
            </View>
          </AnimatedPressable>
        </View>
      </FadeInView>

      {/* Inspection List Section */}
      <View style={styles.listSection}>
        <View style={styles.listHeaderRow}>
          <View>
            <Text style={styles.listTitle}>Mandi Inspection Records</Text>
            <Text style={styles.listSubtitle}>
              {filteredInspections.length} recorded appraisals
            </Text>
          </View>

          {/* Filter Chips */}
          <View style={styles.filterGroup}>
            {(['ALL', 'FINALIZED', 'REVIEW'] as const).map((tab) => {
              const active = filter === tab;
              return (
                <AnimatedPressable
                  key={tab}
                  haptic="selection"
                  onPress={() => setFilter(tab)}
                  style={[
                    styles.filterChip,
                    active && styles.filterChipActive,
                  ]}
                >
                  <Text
                    style={[
                      styles.filterChipText,
                      active && styles.filterChipTextActive,
                    ]}
                  >
                    {tab === 'ALL' ? 'All' : tab === 'FINALIZED' ? 'Certified' : 'Pending'}
                  </Text>
                </AnimatedPressable>
              );
            })}
          </View>
        </View>

        {loading ? (
          <View style={{ marginTop: Spacing.md }}>
            <SkeletonInspectionRow />
            <SkeletonInspectionRow />
            <SkeletonInspectionRow />
          </View>
        ) : filteredInspections.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyTitle}>No Inspections in this View</Text>
            <Text style={styles.emptySubtitle}>
              Begin a new onion lot appraisal using the buttons above.
            </Text>
          </View>
        ) : (
          <FlatList
            data={filteredInspections}
            keyExtractor={(item) => item.id}
            showsVerticalScrollIndicator={false}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={onRefresh}
                tintColor="#0c0c0e"
                colors={['#0c0c0e']}
              />
            }
            renderItem={({ item, index }) => {
              const isCertified = item.status === 'FINALIZED';
              const isDraft = item.status === 'DRAFT';
              const accentColor = isCertified ? '#059669' : isDraft ? '#64748b' : '#0284c7';

              return (
                <FadeInView delay={Math.min(index * 40, 200)} distance={8}>
                  <AnimatedPressable
                    haptic="medium"
                    onPress={() => onSelectInspection(item.id)}
                    style={[
                      styles.inspectionCard,
                      { borderLeftColor: accentColor, borderLeftWidth: 3.5 },
                    ]}
                  >
                    <View style={styles.cardTopRow}>
                      <View style={styles.lotIdRow}>
                        <Text style={styles.lotIdText}>
                          {item.lot_id || `LOT #${item.id.slice(0, 8).toUpperCase()}`}
                        </Text>
                        <View style={styles.sampleCountTag}>
                          <Text style={styles.sampleCountText}>
                            {item.sample_count > 0 ? `${item.sample_count} ${item.sample_count === 1 ? 'sample' : 'samples'}` : 'New Lot'}
                          </Text>
                        </View>
                      </View>
                      <GradeBadge grade={item.status} size="sm" />
                    </View>

                    <View style={styles.cardLocationRow}>
                      <Text style={styles.locationPinIcon}>📍</Text>
                      <Text style={styles.procurementCentreText} numberOfLines={1}>
                        {item.procurement_centre || 'Mandi Yard, Lasalgaon APMC'}
                      </Text>
                    </View>

                    {/* Caliber Quality Split Bar */}
                    <View style={styles.caliberBarWrap}>
                      <View style={styles.caliberBarTrack}>
                        <View style={[styles.caliberBarSegment, { flex: isCertified ? 75 : 50, backgroundColor: '#059669' }]} />
                        <View style={[styles.caliberBarSegment, { flex: isCertified ? 18 : 30, backgroundColor: '#d97706' }]} />
                        <View style={[styles.caliberBarSegment, { flex: isCertified ? 7 : 20, backgroundColor: '#dc2626' }]} />
                      </View>
                      <View style={styles.caliberLegendRow}>
                        <Text style={styles.caliberLegendItem}>
                          <Text style={{ color: '#047857', fontWeight: '800' }}>● </Text>
                          Grade A
                        </Text>
                        <Text style={styles.caliberLegendItem}>
                          <Text style={{ color: '#b45309', fontWeight: '800' }}>● </Text>
                          URS
                        </Text>
                        <Text style={styles.caliberLegendItem}>
                          <Text style={{ color: '#b91c1c', fontWeight: '800' }}>● </Text>
                          Rejection
                        </Text>
                        <Text style={styles.caliberLegendAction}>
                          Inspect →
                        </Text>
                      </View>
                    </View>

                    <View style={styles.cardFooter}>
                      <Text style={styles.officerText}>
                        Assessor: {item.officer_name || 'Senior Grader'}
                      </Text>
                      <Text style={styles.dateText}>
                        {new Date(item.created_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </Text>
                    </View>
                  </AnimatedPressable>
                </FadeInView>
              );
            }}
          />
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f7f4',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
  },

  /* Executive Mandi Telemetry Bento Bar */
  kpiRow: {
    flexDirection: 'row',
    marginBottom: 12,
    gap: 8,
  },
  kpiCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    paddingVertical: 10,
    paddingHorizontal: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e5e2db',
    ...Shadows.card,
  },
  kpiCardSlate: {
    borderTopWidth: 3,
    borderTopColor: '#334155',
  },
  kpiCardEmerald: {
    borderTopWidth: 3,
    borderTopColor: '#059669',
    backgroundColor: '#fbfdfc',
  },
  kpiCardCyan: {
    borderTopWidth: 3,
    borderTopColor: '#0284c7',
  },
  kpiHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 3,
  },
  kpiPillTag: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#64748b',
    letterSpacing: 0.5,
  },
  liveEmeraldDot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#10b981',
  },
  kpiValue: {
    fontSize: 20,
    fontWeight: '800',
    color: '#0c0c0e',
    letterSpacing: -0.4,
  },
  kpiUnit: {
    fontSize: 12,
    fontWeight: '600',
    color: '#64748b',
  },
  kpiSubLabel: {
    fontSize: 9.5,
    color: '#64748b',
    marginTop: 2,
    fontWeight: '600',
    textAlign: 'center',
  },

  /* Station Setup Banner */
  stationBanner: {
    width: '100%',
    minHeight: 135,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.12)',
    position: 'relative',
    ...Shadows.cardElevated,
  },
  stationImage: {
    width: '100%',
    height: '100%',
    position: 'absolute',
    inset: 0,
  },
  stationOverlay: {
    backgroundColor: 'rgba(12, 12, 14, 0.78)',
    padding: 14,
    justifyContent: 'center',
  },
  stationBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  stationBadge: {
    backgroundColor: 'rgba(56, 189, 248, 0.2)',
    paddingHorizontal: 7,
    paddingVertical: 2.5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.35)',
  },
  stationBadgeText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#38bdf8',
    letterSpacing: 0.5,
  },
  stationPillSecondary: {
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 6,
    paddingVertical: 2.5,
    borderRadius: 4,
  },
  stationPillSecondaryText: {
    fontSize: 8.5,
    fontWeight: '700',
    color: '#e2e8f0',
    letterSpacing: 0.5,
  },
  stationTitle: {
    fontSize: 14.5,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  stationDesc: {
    fontSize: 11,
    color: '#cbd5e1',
    marginTop: 3,
    lineHeight: 15,
  },
  stationChipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 8,
  },
  stationChip: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingHorizontal: 7,
    paddingVertical: 2.5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.14)',
  },
  stationChipText: {
    fontSize: 9.5,
    fontWeight: '600',
    color: '#f1f5f9',
  },

  /* Action Center */
  heroActionCard: {
    backgroundColor: '#0c0c0e',
    borderRadius: Radius.lg,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.14)',
    ...Shadows.cardElevated,
  },
  heroContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  heroAperturePod: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
  },
  heroApertureIcon: {
    fontSize: 20,
  },
  heroTextContainer: {
    flex: 1,
  },
  heroMicroPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(16, 185, 129, 0.18)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginBottom: 3,
  },
  heroDotLive: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#10b981',
  },
  heroMicroPillText: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#34d399',
    letterSpacing: 0.5,
  },
  heroTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  heroSubtitle: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
    lineHeight: 15,
  },
  heroChevronBadge: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 18,
    ...Shadows.sm,
  },
  heroChevron: {
    color: '#0c0c0e',
    fontSize: 11.5,
    fontWeight: '800',
  },
  rapidActionRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  rapidCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    padding: 11,
    borderWidth: 1,
    borderColor: '#e5e2db',
    ...Shadows.card,
  },
  rapidCardDemo: {
    backgroundColor: '#fffdf9',
    borderColor: '#fed7aa',
  },
  rapidIconPod: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: '#f1f5f9',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 6,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  rapidIconPodAmber: {
    backgroundColor: '#fef3c7',
    borderColor: '#fde68a',
  },
  rapidIcon: {
    fontSize: 14,
    fontWeight: '800',
    color: '#0f172a',
  },
  rapidIconAmber: {
    fontSize: 15,
    color: '#d97706',
  },
  rapidTitle: {
    fontSize: 12.5,
    fontWeight: '700',
    color: '#0f172a',
  },
  rapidSubtitle: {
    fontSize: 10,
    color: '#64748b',
    marginTop: 2,
    lineHeight: 13,
  },
  rapidTag: {
    alignSelf: 'flex-start',
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 5,
    paddingVertical: 1.5,
    borderRadius: 3,
    marginTop: 8,
  },
  rapidTagText: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#475569',
    letterSpacing: 0.3,
  },
  demoLotBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#ecfdf5',
    paddingHorizontal: 6,
    paddingVertical: 1.5,
    borderRadius: 3,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#a7f3d0',
  },
  demoLotBadgeText: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#047857',
    letterSpacing: 0.3,
  },

  /* List Section */
  listSection: {
    flex: 1,
  },
  listHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  listTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#0c0c0e',
    letterSpacing: -0.2,
  },
  listSubtitle: {
    fontSize: 10.5,
    color: '#64748b',
    marginTop: 1,
  },
  filterGroup: {
    flexDirection: 'row',
    backgroundColor: '#f1f5f9',
    borderRadius: 6,
    padding: 2,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  filterChip: {
    paddingHorizontal: 9,
    paddingVertical: 3.5,
    borderRadius: 4,
  },
  filterChipActive: {
    backgroundColor: '#0c0c0e',
  },
  filterChipText: {
    fontSize: 10.5,
    color: '#64748b',
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: '#ffffff',
    fontWeight: '700',
  },
  listContent: {
    paddingBottom: Spacing.xxl,
  },
  inspectionCard: {
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    padding: 13,
    borderWidth: 1,
    borderColor: '#e5e2db',
    marginBottom: 10,
    ...Shadows.card,
  },
  cardTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  lotIdRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  lotIdText: {
    fontSize: 13.5,
    fontWeight: '800',
    color: '#0f172a',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    letterSpacing: -0.3,
  },
  sampleCountTag: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 6,
    paddingVertical: 1.5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  sampleCountText: {
    fontSize: 9.5,
    color: '#475569',
    fontWeight: '700',
  },
  cardLocationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    marginTop: 6,
  },
  locationPinIcon: {
    fontSize: 11,
  },
  procurementCentreText: {
    fontSize: 11.5,
    color: '#475569',
    fontWeight: '500',
  },
  caliberBarWrap: {
    marginTop: 9,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
  },
  caliberBarTrack: {
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#e2e8f0',
    flexDirection: 'row',
    overflow: 'hidden',
    marginBottom: 5,
  },
  caliberBarSegment: {
    height: '100%',
  },
  caliberLegendRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  caliberLegendItem: {
    fontSize: 9.5,
    color: '#64748b',
    fontWeight: '600',
  },
  caliberLegendAction: {
    fontSize: 10,
    color: '#0284c7',
    fontWeight: '700',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 7,
    borderTopWidth: 1,
    borderTopColor: '#f8fafc',
  },
  officerText: {
    fontSize: 10.5,
    color: '#64748b',
    fontWeight: '500',
  },
  dateText: {
    fontSize: 10,
    color: '#94a3b8',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  emptyContainer: {
    padding: Spacing.hero,
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    alignItems: 'center',
    marginTop: Spacing.md,
    borderWidth: 1,
    borderColor: '#e5e2db',
  },
  emptyTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0c0c0e',
  },
  emptySubtitle: {
    fontSize: 12,
    color: '#71717a',
    textAlign: 'center',
    marginTop: 4,
    lineHeight: 16,
  },
});
