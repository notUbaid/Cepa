import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { InspectionSummary } from '../types';

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
    setRefreshing(true);
    loadData();
  };

  const getStatusPill = (status: string) => {
    switch (status) {
      case 'FINALIZED':
        return { bg: '#27ae60', text: 'FINALIZED' };
      case 'REVIEW':
        return { bg: '#f39c12', text: 'IN REVIEW' };
      case 'PROCESSING':
        return { bg: '#2980b9', text: 'PROCESSING' };
      default:
        return { bg: '#7f8c8d', text: 'DRAFT' };
    }
  };

  return (
    <View style={styles.container}>
      {/* Primary Call to Action */}
      <View style={styles.actionCard}>
        <View style={styles.actionHeader}>
          <Text style={styles.actionTitle}>Onion Procurement Inspection</Text>
          <Text style={styles.actionDesc}>
            Spread sample lot with ChArUco calibration card to inspect quality & size.
          </Text>
        </View>
        <TouchableOpacity
          style={styles.startBtn}
          onPress={onStartNewInspection}
        >
          <Text style={styles.startBtnText}>+ Start New Inspection</Text>
        </TouchableOpacity>
      </View>

      {/* System Status Banner */}
      {cvInfo && (
        <View style={styles.sysCard}>
          <Text style={styles.sysTitle}>SYSTEM ENGINE STATUS</Text>
          <View style={styles.sysRow}>
            <Text style={styles.sysLabel}>Segmentation:</Text>
            <Text style={styles.sysValue}>{cvInfo.seg_provider}</Text>
          </View>
          <View style={styles.sysRow}>
            <Text style={styles.sysLabel}>Defect Classifier:</Text>
            <Text style={styles.sysValue}>{cvInfo.defect_classifier}</Text>
          </View>
          <View style={styles.sysRow}>
            <Text style={styles.sysLabel}>Active Policy:</Text>
            <Text style={styles.sysValue}>{cvInfo.active_policy}</Text>
          </View>
          {cvInfo.warning && (
            <View style={styles.warningBox}>
              <Text style={styles.warningText}>⚠️ {cvInfo.warning}</Text>
            </View>
          )}
        </View>
      )}

      {/* Inspection History List */}
      <View style={styles.listSection}>
        <View style={styles.listHeaderRow}>
          <Text style={styles.listTitle}>Recent Inspections</Text>
          <Text style={styles.listCount}>{inspections.length} recorded</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color="#38bdf8" style={{ marginTop: 24 }} />
        ) : inspections.length === 0 ? (
          <View style={styles.emptyCard}>
            <Text style={styles.emptyTitle}>No Inspections Yet</Text>
            <Text style={styles.emptyDesc}>
              Tap the button above to start your first onion lot quality appraisal.
            </Text>
          </View>
        ) : (
          <FlatList
            data={inspections}
            keyExtractor={(item) => item.id}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
            }
            renderItem={({ item }) => {
              const pill = getStatusPill(item.status);
              return (
                <TouchableOpacity
                  style={styles.itemCard}
                  onPress={() => onSelectInspection(item.id)}
                >
                  <View style={styles.itemTopRow}>
                    <Text style={styles.itemLotId}>
                      {item.lot_id || 'Lot # (Unspecified)'}
                    </Text>
                    <View style={[styles.pill, { backgroundColor: pill.bg }]}>
                      <Text style={styles.pillText}>{pill.text}</Text>
                    </View>
                  </View>

                  <Text style={styles.itemCenter}>
                    {item.procurement_centre || 'Procurement Centre Not Specified'}
                  </Text>

                  <View style={styles.itemBottomRow}>
                    <Text style={styles.itemOfficer}>
                      Officer: {item.officer_name || 'N/A'}
                    </Text>
                    <Text style={styles.itemDate}>
                      {new Date(item.created_at).toLocaleDateString()}
                    </Text>
                  </View>
                </TouchableOpacity>
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
    backgroundColor: '#0d1b2a',
    padding: 16,
  },
  actionCard: {
    backgroundColor: '#1b263b',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2e3d52',
    marginBottom: 14,
  },
  actionHeader: {
    marginBottom: 12,
  },
  actionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  actionDesc: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 4,
    lineHeight: 18,
  },
  startBtn: {
    backgroundColor: '#0284c7',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  startBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  sysCard: {
    backgroundColor: '#162232',
    borderRadius: 10,
    padding: 12,
    marginBottom: 14,
    borderLeftWidth: 3,
    borderLeftColor: '#38bdf8',
  },
  sysTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: '#94a3b8',
    letterSpacing: 1,
    marginBottom: 6,
  },
  sysRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 2,
  },
  sysLabel: {
    fontSize: 11,
    color: '#94a3b8',
  },
  sysValue: {
    fontSize: 11,
    fontWeight: '600',
    color: '#e2e8f0',
  },
  warningBox: {
    marginTop: 6,
    padding: 6,
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
    borderRadius: 4,
  },
  warningText: {
    fontSize: 10,
    color: '#ff7675',
  },
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
    fontSize: 15,
    fontWeight: '700',
    color: '#f8f9fa',
  },
  listCount: {
    fontSize: 11,
    color: '#64748b',
  },
  emptyCard: {
    padding: 24,
    backgroundColor: '#162232',
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 16,
  },
  emptyTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#e2e8f0',
  },
  emptyDesc: {
    fontSize: 12,
    color: '#64748b',
    textAlign: 'center',
    marginTop: 6,
  },
  itemCard: {
    backgroundColor: '#1b263b',
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#243347',
  },
  itemTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  itemLotId: {
    fontSize: 14,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  pill: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  pillText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#fff',
    letterSpacing: 0.5,
  },
  itemCenter: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 4,
  },
  itemBottomRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#243347',
    paddingTop: 6,
  },
  itemOfficer: {
    fontSize: 11,
    color: '#64748b',
  },
  itemDate: {
    fontSize: 11,
    color: '#64748b',
  },
});
