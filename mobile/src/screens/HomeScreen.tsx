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
import { Feather } from '@expo/vector-icons';
import { ApiClient } from '../api/client';
import { InspectionSummary } from '../types';
import { DemoVideoModal } from '../components/DemoVideoModal';
import { CANONICAL_DEMO_INSPECTION_ID } from '../data/canonicalDemoData';
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
  onStartNewInspection: (mode?: 'CAMERA' | 'UPLOAD' | 'VIDEO') => void;
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
  const [videoModalVisible, setVideoModalVisible] = useState(false);
  const [isLive, setIsLive] = useState<boolean>(true);

  const handleLoadDemoLot = async () => {
    Haptics.heavy();
    setLoadingDemoLot(true);
    try {
      // 1. Try to load the verified canonical demo inspection directly
      try {
        const demoInsp = await ApiClient.seedDemoInspection(false);
        if (demoInsp && demoInsp.id) {
          onSelectInspection(demoInsp.id);
          return;
        }
      } catch (err) {
        console.warn('Direct seedDemoInspection failed, falling back:', err);
      }

      // 2. Fallback: check existing list for a valid multi-bulb inspection
      const list = await ApiClient.listInspections().catch(() => []);
      const existing = list.find((i) => (i.lot_id || '').includes('DEMO') && (i.total_bulbs || 0) >= 10);
      if (existing) {
        onSelectInspection(existing.id);
        return;
      }

      // 3. Fallback directly to canonical offline demo lot without delay
      onSelectInspection(CANONICAL_DEMO_INSPECTION_ID);
    } catch (e: any) {
      console.warn('Loading offline demo lot on fallback:', e);
      onSelectInspection(CANONICAL_DEMO_INSPECTION_ID);
    } finally {
      setLoadingDemoLot(false);
    }
  };

  const loadData = async () => {
    try {
      const list = await ApiClient.listInspections();
      if (!list || list.length === 0) {
        setIsLive(false);
        // Pre-populate with canonical demo lot so the screen is never blank during cold start
        setInspections([
          {
            id: CANONICAL_DEMO_INSPECTION_ID,
            lot_id: 'LOT-NASHIK-RED-DEMO',
            farmer_name: 'Devidas Sonawane',
            procurement_centre: 'Lasalgaon APMC Mandi, Nashik',
            officer_name: 'Senior Grader S. Patil',
            status: 'FINALIZED',
            created_at: new Date().toISOString(),
            finalized_at: new Date().toISOString(),
            sample_count: 1,
            total_bulbs: 24,
            grade_a_pct: 83.3,
            urs_pct: 12.5,
            rejected_pct: 0.0,
          },
        ]);
      } else {
        setIsLive(true);
        setInspections(list);
      }
    } catch (e) {
      console.warn('Failed to load home data, seeding demo lot:', e);
      setIsLive(false);
      setInspections([
        {
          id: CANONICAL_DEMO_INSPECTION_ID,
          lot_id: 'LOT-NASHIK-RED-DEMO',
          farmer_name: 'Devidas Sonawane',
          procurement_centre: 'Lasalgaon APMC Mandi, Nashik',
          officer_name: 'Senior Grader S. Patil',
          status: 'FINALIZED',
          created_at: new Date().toISOString(),
          finalized_at: new Date().toISOString(),
          sample_count: 1,
          total_bulbs: 24,
          grade_a_pct: 83.3,
          urs_pct: 12.5,
          rejected_pct: 0.0,
        },
      ]);
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

  return (
    <View style={styles.container}>
      {/* Network / Execution Mode Banner */}
      <View style={isLive ? styles.liveStatusBanner : styles.demoStatusBanner}>
        <View style={isLive ? styles.liveStatusDot : styles.demoStatusDot} />
        <Text style={isLive ? styles.liveStatusText : styles.demoStatusText}>
          {isLive
            ? 'LIVE MANDI TELEMETRY — Connected to Assaying Gateway'
            : 'CACHED SAMPLE: backend unreachable. Not a live analysis.'}
        </Text>
      </View>

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
                  <Feather name="layers" size={11} color="#64748b" />
                  <Text style={styles.kpiPillTag}>TOTAL LOTS</Text>
                </View>
                <Text style={styles.kpiValue}>{totalLots}</Text>
                <Text style={styles.kpiSubLabel}>Recorded Appraisals</Text>
              </View>

              <View style={[styles.kpiCard, styles.kpiCardEmerald]}>
                <View style={styles.kpiHeaderRow}>
                  <Feather name="award" size={11} color="#059669" />
                  <Text style={[styles.kpiPillTag, { color: '#059669' }]}>GRADE A</Text>
                </View>
                <Text style={[styles.kpiValue, { color: '#059669' }]}>{finalizedLots}</Text>
                <Text style={styles.kpiSubLabel}>
                  {totalLots > 0 ? `${Math.round((finalizedLots / totalLots) * 100)}% Certified` : '0% Certified'}
                </Text>
              </View>

              <View style={[styles.kpiCard, styles.kpiCardCyan]}>
                <View style={styles.kpiHeaderRow}>
                  <Feather name="crosshair" size={11} color="#0284c7" />
                  <Text style={[styles.kpiPillTag, { color: '#0284c7' }]}>METROLOGY</Text>
                </View>
                <Text style={[styles.kpiValue, { color: '#0369a1' }]}>
                  ±0.4<Text style={styles.kpiUnit}>mm</Text>
                </Text>
                <Text style={styles.kpiSubLabel}>Planar (3D ±1.5mm)</Text>
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
                <Feather name="cpu" size={10} color="#38bdf8" style={{ marginRight: 4 }} />
                <Text style={styles.stationBadgeText}>AI QUALITY SUITE</Text>
              </View>
              <View style={styles.stationPillSecondary}>
                <Text style={styles.stationPillSecondaryText}>GROQ MULTIMODAL</Text>
              </View>
            </View>
            <Text style={styles.stationTitle}>Autonomous Mandi Quality Terminal</Text>
            <Text style={styles.stationDesc}>
              Continuous video sweeps or top-down photo inspection. Real-time rot detection, ChArUco planar sizing, and APMC valuation in seconds.
            </Text>
            <View style={styles.stationChipRow}>
              <View style={styles.stationChip}>
                <Feather name="video" size={10} color="#38bdf8" style={{ marginRight: 4 }} />
                <Text style={styles.stationChipText}>Video Sorter</Text>
              </View>
              <View style={styles.stationChip}>
                <Feather name="shield" size={10} color="#34d399" style={{ marginRight: 4 }} />
                <Text style={styles.stationChipText}>Rot Defense</Text>
              </View>
              <View style={styles.stationChip}>
                <Feather name="trending-up" size={10} color="#fbbf24" style={{ marginRight: 4 }} />
                <Text style={styles.stationChipText}>Mandi Payout</Text>
              </View>
              <View style={styles.stationChip}>
                <Feather name="archive" size={10} color="#c084fc" style={{ marginRight: 4 }} />
                <Text style={styles.stationChipText}>Storage Horizon</Text>
              </View>
            </View>
          </View>
        </View>
      </FadeInView>

      {/* Action Center */}
      <FadeInView delay={110} distance={12}>
        {/* Flagship: Video Sweep Inspection Action Card */}
        <AnimatedPressable
          haptic="heavy"
          onPress={() => onStartNewInspection('VIDEO')}
          style={[styles.heroActionCard, { borderColor: 'rgba(56, 189, 248, 0.35)', marginBottom: 8 }]}
        >
          <View style={styles.heroContent}>
            <View style={[styles.heroAperturePod, { borderColor: 'rgba(56, 189, 248, 0.5)' }]}>
              <Feather name="video" size={18} color="#38bdf8" />
            </View>
            <View style={styles.heroTextContainer}>
              <View style={[styles.heroMicroPill, { backgroundColor: 'rgba(56, 189, 248, 0.18)' }]}>
                <View style={[styles.heroDotLive, { backgroundColor: '#38bdf8' }]} />
                <Text style={[styles.heroMicroPillText, { color: '#38bdf8' }]}>REAL-TIME VIDEO SWEEP</Text>
              </View>
              <Text style={styles.heroTitle}>Video Sweep &amp; Sorter</Text>
              <Text style={styles.heroSubtitle}>
                Pan camera across lot or inspect one by one with live defect timestamps
              </Text>
            </View>
            <View style={styles.nestedButton}>
              <Text style={styles.nestedButtonText}>Sweep</Text>
              <View style={styles.nestedButtonIcon}>
                <Feather name="arrow-right" size={11} color="#09090b" />
              </View>
            </View>
          </View>
        </AnimatedPressable>

        {/* Photo Spread Scanner Card */}
        <AnimatedPressable
          haptic="heavy"
          onPress={() => onStartNewInspection('CAMERA')}
          style={styles.heroActionCardLight}
        >
          <View style={styles.heroContent}>
            <View style={styles.heroAperturePodLight}>
              <Feather name="camera" size={18} color="#0f172a" />
            </View>
            <View style={styles.heroTextContainer}>
              <View style={styles.heroMicroPillSlate}>
                <Text style={styles.heroMicroPillTextSlate}>PRECISION OPTICAL CALIPER</Text>
              </View>
              <Text style={styles.heroTitleDark}>Photo Lot Inspection</Text>
              <Text style={styles.heroSubtitleDark}>
                Capture an overhead photo of an onion spread for instant caliber sizing
              </Text>
            </View>
            <View style={styles.nestedButtonDark}>
              <Text style={styles.nestedButtonDarkText}>Snap</Text>
              <View style={styles.nestedButtonDarkIcon}>
                <Feather name="arrow-right" size={11} color="#ffffff" />
              </View>
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
              <Feather name="upload-cloud" size={16} color="#0f172a" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rapidTitle}>Upload Media File</Text>
              <Text style={styles.rapidSubtitle}>
                Select photo or video from device
              </Text>
            </View>
            <View style={styles.rapidTag}>
              <Text style={styles.rapidTagText}>GALLERY</Text>
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
              <Feather name="zap" size={16} color="#b45309" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.rapidTitle}>Load Synthetic Demo Sample</Text>
              <Text style={styles.rapidSubtitle}>
                22 bulbs · Synthetic composite image
              </Text>
            </View>
            <View style={styles.demoLotBadge}>
              <Text style={styles.demoLotBadgeText}>DEMO</Text>
            </View>
          </AnimatedPressable>
        </View>

        {/* Zero-Latency Mandi Video Sweep Demo Banner */}
        <AnimatedPressable
          haptic="medium"
          onPress={() => setVideoModalVisible(true)}
          style={styles.demoVideoBanner}
        >
          <View style={styles.demoVideoIconPod}>
            <Feather name="play-circle" size={18} color="#0284c7" />
          </View>
          <View style={{ flex: 1 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Text style={styles.demoVideoTitle}>Watch Mandi Video Sweep</Text>
              <View style={styles.demoModeBadge}>
                <Text style={styles.demoModeBadgeText}>DEMO MODE</Text>
              </View>
            </View>
            <Text style={styles.demoVideoSubtitle}>
              Continuous conveyor sweep proof · Real-time optical caliper &amp; sorting HUD
            </Text>
          </View>
          <View style={styles.demoVideoArrow}>
            <Feather name="chevron-right" size={16} color="#0284c7" />
          </View>
        </AnimatedPressable>
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

              return (
                <FadeInView delay={Math.min(index * 40, 200)} distance={8}>
                  <AnimatedPressable
                    haptic="medium"
                    onPress={() => onSelectInspection(item.id)}
                    style={styles.inspectionCard}
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
                      <Feather name="map-pin" size={11} color="#64748b" style={{ marginRight: 5 }} />
                      <Text style={styles.procurementCentreText} numberOfLines={1}>
                        {item.farmer_name ? `${item.farmer_name} · ` : ''}{item.procurement_centre || 'Mandi Yard, Lasalgaon APMC'}
                      </Text>
                    </View>

                    {/* Caliber Quality Split Bar */}
                    {item.total_bulbs && item.total_bulbs > 0 ? (
                      <View style={styles.caliberBarWrap}>
                        <View style={styles.caliberBarTrack}>
                          <View
                            style={[
                              styles.caliberBarSegment,
                              {
                                flex: Math.max(item.grade_a_pct ?? 0, 1),
                                backgroundColor: '#059669',
                              },
                            ]}
                          />
                          <View
                            style={[
                              styles.caliberBarSegment,
                              {
                                flex: Math.max(item.urs_pct ?? 0, 0.5),
                                backgroundColor: '#d97706',
                              },
                            ]}
                          />
                          <View
                            style={[
                              styles.caliberBarSegment,
                              {
                                flex: Math.max(item.rejected_pct ?? 0, 0.5),
                                backgroundColor: '#dc2626',
                              },
                            ]}
                          />
                        </View>
                        <View style={styles.caliberLegendRow}>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#059669' }} />
                            <Text style={styles.caliberLegendItem}>Grade A {item.grade_a_pct?.toFixed(0)}%</Text>
                          </View>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#d97706' }} />
                            <Text style={styles.caliberLegendItem}>URS {item.urs_pct?.toFixed(0)}%</Text>
                          </View>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#dc2626' }} />
                            <Text style={styles.caliberLegendItem}>Rej {item.rejected_pct?.toFixed(0)}%</Text>
                          </View>
                          <View style={styles.inspectActionPill}>
                            <Text style={styles.caliberLegendAction}>View</Text>
                            <Feather name="chevron-right" size={12} color="#0f172a" />
                          </View>
                        </View>
                      </View>
                    ) : (
                      <View style={[styles.caliberBarWrap, { paddingVertical: 4 }]}>
                        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#0284c7' }} />
                            <Text style={[styles.caliberLegendItem, { color: '#0369a1', fontWeight: '600' }]}>
                              {item.sample_count > 0 ? `${item.sample_count} sample captured · Tap to review` : 'Ready for optical capture'}
                            </Text>
                          </View>
                          <View style={styles.inspectActionPill}>
                            <Text style={styles.caliberLegendAction}>Open</Text>
                            <Feather name="chevron-right" size={12} color="#0f172a" />
                          </View>
                        </View>
                      </View>
                    )}

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

      {/* Mandi Video Sweep Walkthrough Modal */}
      <DemoVideoModal
        visible={videoModalVisible}
        onClose={() => setVideoModalVisible(false)}
        onExploreDemoLot={() => {
          setVideoModalVisible(false);
          handleLoadDemoLot();
        }}
      />
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
  heroActionCardLight: {
    backgroundColor: '#ffffff',
    borderRadius: Radius.lg,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    ...Shadows.card,
  },
  heroContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  heroAperturePod: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.35)',
  },
  heroAperturePodLight: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: '#f8fafc',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  heroTextContainer: {
    flex: 1,
  },
  heroMicroPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(56, 189, 248, 0.18)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginBottom: 3,
  },
  heroMicroPillSlate: {
    alignSelf: 'flex-start',
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginBottom: 3,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  heroDotLive: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#38bdf8',
  },
  heroMicroPillText: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#38bdf8',
    letterSpacing: 0.5,
  },
  heroMicroPillTextSlate: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#475569',
    letterSpacing: 0.5,
  },
  heroTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  heroTitleDark: {
    fontSize: 15,
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: -0.2,
  },
  heroSubtitle: {
    fontSize: 11,
    color: '#94a3b8',
    marginTop: 2,
    lineHeight: 15,
  },
  heroSubtitleDark: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
    lineHeight: 15,
  },
  nestedButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#38bdf8',
    paddingLeft: 10,
    paddingRight: 5,
    paddingVertical: 5,
    borderRadius: 20,
  },
  nestedButtonText: {
    color: '#09090b',
    fontSize: 11.5,
    fontWeight: '800',
  },
  nestedButtonIcon: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: 'rgba(9, 9, 11, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  nestedButtonDark: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#0f172a',
    paddingLeft: 10,
    paddingRight: 5,
    paddingVertical: 5,
    borderRadius: 20,
  },
  nestedButtonDarkText: {
    color: '#ffffff',
    fontSize: 11.5,
    fontWeight: '800',
  },
  nestedButtonDarkIcon: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
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
    borderRadius: Radius.lg,
    padding: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
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
    marginTop: 6,
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
  inspectActionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 7,
    paddingVertical: 2.5,
    borderRadius: 12,
  },
  caliberLegendAction: {
    fontSize: 10,
    color: '#0f172a',
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

  /* Video Sweep Fallback Banner */
  demoVideoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0f9ff',
    borderRadius: Radius.md,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#bae6fd',
    marginTop: 8,
    ...Shadows.card,
  },
  demoVideoIconPod: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(2, 132, 199, 0.12)',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  demoVideoTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0369a1',
  },
  demoModeBadge: {
    backgroundColor: '#e0f2fe',
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
  },
  demoModeBadgeText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#0284c7',
    letterSpacing: 0.5,
  },
  demoVideoSubtitle: {
    fontSize: 11,
    color: '#0284c7',
    marginTop: 2,
  },
  demoVideoArrow: {
    marginLeft: 6,
  },
  liveStatusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ecfdf5',
    borderColor: '#a7f3d0',
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingVertical: 6,
    paddingHorizontal: 10,
    marginBottom: 10,
  },
  demoStatusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fffbeb',
    borderColor: '#fde68a',
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingVertical: 6,
    paddingHorizontal: 10,
    marginBottom: 10,
  },
  liveStatusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: '#059669',
    marginRight: 8,
  },
  demoStatusDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: '#d97706',
    marginRight: 8,
  },
  liveStatusText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#065f46',
    letterSpacing: 0.3,
  },
  demoStatusText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#92400e',
    letterSpacing: 0.3,
  },
});
