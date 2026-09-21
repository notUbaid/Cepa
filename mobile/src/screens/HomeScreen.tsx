import React, { useEffect, useState } from 'react';
import {
  FlatList,
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
  const [cvInfo, setCvInfo] = useState<any>(null);
  const [filter, setFilter] = useState<'ALL' | 'FINALIZED' | 'REVIEW'>('ALL');

  const loadData = async () => {
    try {
      const [list, cv] = await Promise.all([
        ApiClient.listInspections().catch(() => []),
        ApiClient.checkCvHealth().catch(() => null),
      ]);
      setInspections(list);
      setCvInfo(cv);
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
              <View style={[styles.kpiCard, { borderColor: Colors.accent }]}>
                <Text style={[styles.kpiValue, { color: Colors.accent }]}>{totalLots}</Text>
                <Text style={styles.kpiLabel}>Total Lots</Text>
              </View>
              <View style={[styles.kpiCard, { borderColor: Colors.gradeA }]}>
                <Text style={[styles.kpiValue, { color: Colors.gradeA }]}>{finalizedLots}</Text>
                <Text style={styles.kpiLabel}>Certified</Text>
              </View>
              <View style={[styles.kpiCard, { borderColor: Colors.urs }]}>
                <Text style={[styles.kpiValue, { color: Colors.urs }]}>{inReviewLots}</Text>
                <Text style={styles.kpiLabel}>Pending / Review</Text>
              </View>
            </>
          )}
        </View>
      </FadeInView>

      {/* Hero Action: Start Inspection */}
      <FadeInView delay={120} distance={15}>
        <AnimatedPressable
          haptic="medium"
          onPress={onStartNewInspection}
          style={styles.heroActionCard}
        >
          <View style={styles.heroContent}>
            <View style={styles.heroIconBadge}>
              <Text style={styles.heroIcon}>📷</Text>
            </View>
            <View style={styles.heroTextContainer}>
              <Text style={styles.heroTitle}>Start Mandi Inspection</Text>
              <Text style={styles.heroSubtitle}>
                ChArUco calibration, YOLO11 segmentation & MobileNetV3 defect appraisal
              </Text>
            </View>
            <View style={styles.heroChevronBadge}>
              <Text style={styles.heroChevron}>→</Text>
            </View>
          </View>
        </AnimatedPressable>
      </FadeInView>

      {/* Engine Status Bar */}
      {cvInfo && (
        <FadeInView delay={180} distance={12}>
          <View style={styles.engineCard}>
            <View style={styles.engineHeader}>
              <Text style={styles.engineTitle}>ENGINE DIAGNOSTICS</Text>
              <Text style={styles.engineVersion}>
                {cvInfo.defect_classifier?.includes('real_onions')
                  ? 'Real Onion MobileNetV3'
                  : 'Multi-Label ResNet'}
              </Text>
            </View>
            <View style={styles.engineGrid}>
              <View style={styles.engineCol}>
                <Text style={styles.engineLabel}>Segmenter</Text>
                <Text style={styles.engineValue}>{cvInfo.seg_provider || 'YOLO11-seg'}</Text>
              </View>
              <View style={styles.engineCol}>
                <Text style={styles.engineLabel}>Standard</Text>
                <Text style={styles.engineValue}>BIS IS 17912:2022</Text>
              </View>
              <View style={styles.engineCol}>
                <Text style={styles.engineLabel}>Accuracy</Text>
                <Text style={[styles.engineValue, { color: Colors.gradeA }]}>98.8% Val</Text>
              </View>
            </View>
          </View>
        </FadeInView>
      )}

      {/* Inspection List Section */}
      <View style={styles.listSection}>
        <View style={styles.listHeaderRow}>
          <View>
            <Text style={styles.listTitle}>Mandi Inspection Logs</Text>
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
            <Text style={styles.emptyIcon}>📦</Text>
            <Text style={styles.emptyTitle}>No Inspections in this View</Text>
            <Text style={styles.emptySubtitle}>
              Start a new inspection using the camera action button above.
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
                tintColor={Colors.accent}
                colors={[Colors.accent]}
              />
            }
            renderItem={({ item, index }) => (
              <FadeInView delay={Math.min(index * 60, 300)} distance={10}>
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
                    📍 {item.procurement_centre || 'Procurement Centre Not Specified'}
                  </Text>

                  <View style={styles.cardFooter}>
                    <Text style={styles.officerText}>
                      Officer: {item.officer_name || 'Standard Evaluator'}
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
    backgroundColor: Colors.bg,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
  },
  kpiRow: {
    flexDirection: 'row',
    marginBottom: Spacing.md,
    gap: Spacing.sm,
  },
  kpiCard: {
    flex: 1,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.sm,
    alignItems: 'center',
    borderWidth: 1,
  },
  kpiValue: {
    fontSize: 22,
    fontWeight: '800',
    fontFamily: 'monospace',
    letterSpacing: -0.5,
  },
  kpiLabel: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 2,
    fontWeight: '500',
  },
  heroActionCard: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1.5,
    borderColor: Colors.accent,
    marginBottom: Spacing.md,
    ...PlatformSelectShadow(),
  },
  heroContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  heroIconBadge: {
    width: 44,
    height: 44,
    borderRadius: Radius.md,
    backgroundColor: Colors.accentSubtle,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  heroIcon: {
    fontSize: 22,
  },
  heroTextContainer: {
    flex: 1,
  },
  heroTitle: {
    ...Typography.title2,
    color: Colors.text,
  },
  heroSubtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 2,
    lineHeight: 15,
  },
  heroChevronBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
  },
  heroChevron: {
    color: Colors.bg,
    fontSize: 14,
    fontWeight: '800',
  },
  engineCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    marginBottom: Spacing.md,
  },
  engineHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  engineTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: Colors.accent,
    letterSpacing: 0.8,
  },
  engineVersion: {
    fontSize: 10,
    color: Colors.textDim,
    fontFamily: 'monospace',
  },
  engineGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 4,
  },
  engineCol: {
    flex: 1,
  },
  engineLabel: {
    fontSize: 10,
    color: Colors.textDim,
  },
  engineValue: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginTop: 1,
    fontFamily: 'monospace',
  },
  listSection: {
    flex: 1,
  },
  listHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  listTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: Colors.text,
  },
  listSubtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 1,
  },
  filterGroup: {
    flexDirection: 'row',
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.sm,
    padding: 2,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  filterChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: Radius.xs,
  },
  filterChipActive: {
    backgroundColor: Colors.accentSubtle,
    borderWidth: 1,
    borderColor: Colors.accent,
  },
  filterChipText: {
    fontSize: 11,
    color: Colors.textDim,
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: Colors.accent,
  },
  listContent: {
    paddingBottom: Spacing.xxl,
  },
  inspectionCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    marginBottom: Spacing.sm,
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
    fontSize: 15,
    fontWeight: '700',
    color: Colors.text,
    letterSpacing: -0.2,
  },
  sampleCountTag: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: Radius.xs,
  },
  sampleCountText: {
    fontSize: 10,
    color: Colors.textDim,
    fontFamily: 'monospace',
  },
  procurementCentreText: {
    fontSize: 12,
    color: Colors.textSecondary,
    marginTop: 6,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
  },
  officerText: {
    fontSize: 11,
    color: Colors.textDim,
  },
  dateText: {
    fontSize: 11,
    color: Colors.textDim,
    fontFamily: 'monospace',
  },
  emptyContainer: {
    padding: Spacing.hero,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    alignItems: 'center',
    marginTop: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  emptyIcon: {
    fontSize: 36,
    marginBottom: Spacing.sm,
  },
  emptyTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.textSecondary,
  },
  emptySubtitle: {
    fontSize: 12,
    color: Colors.textDim,
    textAlign: 'center',
    marginTop: 4,
    lineHeight: 16,
  },
});

function PlatformSelectShadow() {
  return {
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 6,
    elevation: 3,
  };
}
