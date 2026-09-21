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
              <View style={styles.kpiCard}>
                <Text style={styles.kpiValue}>{totalLots}</Text>
                <Text style={styles.kpiLabel}>Total Lots</Text>
              </View>
              <View style={styles.kpiCard}>
                <View style={styles.kpiDotRow}>
                  <View style={[styles.kpiDot, { backgroundColor: Colors.gradeA }]} />
                  <Text style={styles.kpiValue}>{finalizedLots}</Text>
                </View>
                <Text style={styles.kpiLabel}>Certified</Text>
              </View>
              <View style={styles.kpiCard}>
                <View style={styles.kpiDotRow}>
                  <View style={[styles.kpiDot, { backgroundColor: Colors.urs }]} />
                  <Text style={styles.kpiValue}>{inReviewLots}</Text>
                </View>
                <Text style={styles.kpiLabel}>In Review</Text>
              </View>
            </>
          )}
        </View>
      </FadeInView>

      {/* Hero Action: Start Inspection */}
      <FadeInView delay={100} distance={12}>
        <AnimatedPressable
          haptic="medium"
          onPress={onStartNewInspection}
          style={styles.heroActionCard}
        >
          <View style={styles.heroContent}>
            <View style={styles.heroTextContainer}>
              <Text style={styles.heroTitle}>New Inspection</Text>
              <Text style={styles.heroSubtitle}>
                Calibrate reference marker, capture representative spread, and compute net mandi valuation
              </Text>
            </View>
            <View style={styles.heroChevronBadge}>
              <Text style={styles.heroChevron}>→</Text>
            </View>
          </View>
        </AnimatedPressable>
      </FadeInView>

      {/* Inspection List Section */}
      <View style={styles.listSection}>
        <View style={styles.listHeaderRow}>
          <View>
            <Text style={styles.listTitle}>Inspection Records</Text>
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
                    {item.procurement_centre || 'APMC Mandi Yard'}
                  </Text>

                  <View style={styles.cardFooter}>
                    <Text style={styles.officerText}>
                      Officer: {item.officer_name || 'Assessor'}
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
    borderColor: Colors.border,
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
    fontWeight: '700',
    color: Colors.text,
    letterSpacing: -0.3,
  },
  kpiLabel: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 2,
    fontWeight: '500',
  },
  heroActionCard: {
    backgroundColor: Colors.accent,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    marginBottom: Spacing.md,
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
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  heroSubtitle: {
    fontSize: 12,
    color: '#a1a1aa',
    marginTop: 3,
    lineHeight: 17,
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
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.sm,
    padding: 2,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.sm,
  },
  filterChipActive: {
    backgroundColor: Colors.accent,
  },
  filterChipText: {
    fontSize: 11,
    color: Colors.textSecondary,
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: '#ffffff',
    fontWeight: '600',
  },
  listContent: {
    paddingBottom: Spacing.xxl,
  },
  inspectionCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: Spacing.sm,
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
    fontSize: 14,
    fontWeight: '700',
    color: Colors.text,
    letterSpacing: -0.2,
  },
  sampleCountTag: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  sampleCountText: {
    fontSize: 10,
    color: Colors.textSecondary,
    fontWeight: '500',
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
    color: Colors.textMuted,
  },
  dateText: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  emptyContainer: {
    padding: Spacing.hero,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    alignItems: 'center',
    marginTop: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  emptyTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.text,
  },
  emptySubtitle: {
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: 4,
    lineHeight: 16,
  },
});
