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
  onStartNewInspection: () => void;
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
      {/* Quick KPI Overview */}
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
              <View style={styles.kpiCard}>
                <Text style={styles.kpiValue}>{totalLots}</Text>
                <Text style={styles.kpiLabel}>Total Lots</Text>
              </View>
              <View style={styles.kpiCard}>
                <View style={styles.kpiDotRow}>
                  <View style={[styles.kpiDot, { backgroundColor: '#10b981' }]} />
                  <Text style={styles.kpiValue}>{finalizedLots}</Text>
                </View>
                <Text style={styles.kpiLabel}>Certified</Text>
              </View>
              <View style={styles.kpiCard}>
                <View style={styles.kpiDotRow}>
                  <View style={[styles.kpiDot, { backgroundColor: '#f59e0b' }]} />
                  <Text style={styles.kpiValue}>{inReviewLots}</Text>
                </View>
                <Text style={styles.kpiLabel}>In Review</Text>
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
            <View style={styles.stationBadge}>
              <Text style={styles.stationBadgeText}>APMC OPTICAL GRADING BENCH</Text>
            </View>
            <Text style={styles.stationTitle}>70cm Overhead Scanner Protocol</Text>
            <Text style={styles.stationDesc}>
              Single-layer spread with ChArUco 7×5 calibration board for sub-millimeter caliper accuracy.
            </Text>
          </View>
        </View>
      </FadeInView>

      {/* Primary Action Button */}
      <FadeInView delay={110} distance={12}>
        <AnimatedPressable
          haptic="medium"
          onPress={onStartNewInspection}
          style={styles.heroActionCard}
        >
          <View style={styles.heroContent}>
            <View style={styles.heroTextContainer}>
              <Text style={styles.heroTitle}>New Lot Inspection</Text>
              <Text style={styles.heroSubtitle}>
                Calibrate optical marker, scan bulb spread, and compute commercial MSP dockage
              </Text>
            </View>
            <View style={styles.heroChevronBadge}>
              <Text style={styles.heroChevron}>→</Text>
            </View>
          </View>
        </AnimatedPressable>

        {/* 1-Tap Real Mandi Demo Lot Button */}
        <AnimatedPressable
          haptic="heavy"
          onPress={handleLoadDemoLot}
          style={styles.demoLotBannerBtn}
          disabled={loadingDemoLot}
        >
          <View style={styles.demoLotBannerContent}>
            <View style={styles.demoLotIconBox}>
              <Text style={styles.demoLotIcon}>📦</Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.demoLotTitle}>Inspect Verified Mandi Demo Lot</Text>
              <Text style={styles.demoLotSubtitle}>
                Real photographic spread · 24 bulbs · ChArUco 7×5 calibration · NAFED MSP grading
              </Text>
            </View>
            <Text style={styles.demoLotBadge}>24 BULBS</Text>
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
              Begin a new onion lot appraisal using the button above.
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
            renderItem={({ item, index }) => (
              <FadeInView delay={Math.min(index * 50, 250)} distance={8}>
                <AnimatedPressable
                  haptic="medium"
                  onPress={() => onSelectInspection(item.id)}
                  style={styles.inspectionCard}
                >
                  <View style={styles.cardTopRow}>
                    <View style={styles.lotIdRow}>
                      <Text style={styles.lotIdText}>
                        {item.lot_id || `Lot #${item.id.slice(0, 8)}`}
                      </Text>
                      {item.sample_count > 0 && (
                        <View style={styles.sampleCountTag}>
                          <Text style={styles.sampleCountText}>
                            {item.sample_count} {item.sample_count === 1 ? 'sample' : 'samples'}
                          </Text>
                        </View>
                      )}
                    </View>
                    <GradeBadge grade={item.status} size="sm" />
                  </View>

                  <Text style={styles.procurementCentreText} numberOfLines={1}>
                    📍 {item.procurement_centre || 'APMC Mandi Yard'}
                  </Text>

                  <View style={styles.cardFooter}>
                    <Text style={styles.officerText}>
                      Assessor: {item.officer_name || 'Officer'}
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
            )}
          />
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9f8f6',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
  },
  kpiRow: {
    flexDirection: 'row',
    marginBottom: 12,
    gap: Spacing.sm,
  },
  kpiCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    paddingVertical: 12,
    paddingHorizontal: Spacing.sm,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e7e5e4',
    ...Shadows.card,
  },
  kpiDotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  kpiDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  kpiValue: {
    fontSize: 20,
    fontWeight: '800',
    color: '#0c0c0e',
    letterSpacing: -0.3,
  },
  kpiLabel: {
    fontSize: 10.5,
    color: '#71717a',
    marginTop: 2,
    fontWeight: '600',
  },

  /* Station Setup Banner */
  stationBanner: {
    width: '100%',
    height: 125,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.08)',
    position: 'relative',
    ...Shadows.card,
  },
  stationImage: {
    width: '100%',
    height: '100%',
  },
  stationOverlay: {
    position: 'absolute',
    inset: 0,
    backgroundColor: 'rgba(12, 12, 14, 0.72)',
    padding: 12,
    justifyContent: 'center',
  },
  stationBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    alignSelf: 'flex-start',
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 3,
    marginBottom: 4,
  },
  stationBadgeText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#38bdf8',
    letterSpacing: 0.5,
  },
  stationTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  stationDesc: {
    fontSize: 11,
    color: '#d4d4d8',
    marginTop: 3,
    lineHeight: 15,
  },

  /* Hero Action Button */
  heroActionCard: {
    backgroundColor: '#0c0c0e',
    borderRadius: Radius.lg,
    padding: 14,
    marginBottom: 14,
    ...Shadows.card,
  },
  heroContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.md,
  },
  heroTextContainer: {
    flex: 1,
  },
  heroTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  heroSubtitle: {
    fontSize: 11.5,
    color: '#a1a1aa',
    marginTop: 2,
    lineHeight: 16,
  },
  heroChevronBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  heroChevron: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },
  demoLotBannerBtn: {
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    padding: 12,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#e7e5e4',
    ...Shadows.card,
  },
  demoLotBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  demoLotIconBox: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#f4f3ef',
    justifyContent: 'center',
    alignItems: 'center',
  },
  demoLotIcon: {
    fontSize: 18,
  },
  demoLotTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0c0c0e',
  },
  demoLotSubtitle: {
    fontSize: 10.5,
    color: '#71717a',
    marginTop: 2,
    lineHeight: 14,
  },
  demoLotBadge: {
    fontSize: 9.5,
    fontWeight: '800',
    color: '#047857',
    backgroundColor: '#ecfdf5',
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#a7f3d0',
    letterSpacing: 0.4,
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
    fontWeight: '700',
    color: '#0c0c0e',
  },
  listSubtitle: {
    fontSize: 10.5,
    color: '#71717a',
    marginTop: 1,
  },
  filterGroup: {
    flexDirection: 'row',
    backgroundColor: '#f4f3ef',
    borderRadius: 6,
    padding: 2,
    borderWidth: 1,
    borderColor: '#e7e5e4',
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
    color: '#52525b',
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
    borderColor: '#e7e5e4',
    marginBottom: 8,
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
    fontWeight: '700',
    color: '#0c0c0e',
    letterSpacing: -0.2,
  },
  sampleCountTag: {
    backgroundColor: '#f4f3ef',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 3,
    borderWidth: 1,
    borderColor: '#e7e5e4',
  },
  sampleCountText: {
    fontSize: 9.5,
    color: '#52525b',
    fontWeight: '600',
  },
  procurementCentreText: {
    fontSize: 11.5,
    color: '#52525b',
    marginTop: 5,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 7,
    borderTopWidth: 1,
    borderTopColor: '#f5f5f4',
  },
  officerText: {
    fontSize: 10.5,
    color: '#71717a',
    fontWeight: '500',
  },
  dateText: {
    fontSize: 10.5,
    color: '#71717a',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  emptyContainer: {
    padding: Spacing.hero,
    backgroundColor: '#ffffff',
    borderRadius: Radius.md,
    alignItems: 'center',
    marginTop: Spacing.md,
    borderWidth: 1,
    borderColor: '#e7e5e4',
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
