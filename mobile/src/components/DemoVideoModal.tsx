import React from 'react';
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { ApiClient } from '../api/client';
import {
  AnimatedPressable,
  Colors,
  Haptics,
  Radius,
  Shadows,
  Spacing,
  Typography,
} from '../ui';

interface DemoVideoModalProps {
  visible: boolean;
  onClose: () => void;
  onExploreDemoLot: () => void;
}

export const DemoVideoModal: React.FC<DemoVideoModalProps> = ({
  visible,
  onClose,
  onExploreDemoLot,
}) => {
  if (!visible) return null;

  const videoUrl = ApiClient.getDemoSampleVideoUrl();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.modalCard}>
          {/* Modal Header */}
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <View style={styles.badgeRow}>
                <View style={styles.liveBadge}>
                  <View style={styles.liveDot} />
                  <Text style={styles.liveBadgeText}>OPTICAL SWEEP HUD</Text>
                </View>
                <View style={styles.demoModeTag}>
                  <Text style={styles.demoModeTagText}>DEMO MODE</Text>
                </View>
              </View>
              <Text style={styles.title}>Mandi Conveyor Video Sweep</Text>
              <Text style={styles.subtitle}>
                Continuous top-down sweep · Calibrated caliper sizing &amp; rot detection
              </Text>
            </View>
            <Pressable
              onPress={() => {
                Haptics.light();
                onClose();
              }}
              style={styles.closeButton}
              hitSlop={12}
            >
              <Feather name="x" size={20} color="#0f172a" />
            </Pressable>
          </View>

          <ScrollView style={styles.scrollBody} contentContainerStyle={{ paddingBottom: Spacing.lg }}>
            {/* Video Player Container */}
            <View style={styles.videoWrapper}>
              {Platform.OS === 'web' ? (
                // Use standard HTML5 video on web for zero-latency instant playback
                // @ts-ignore - JSX web video element in React Native Web
                <video
                  src={videoUrl}
                  controls
                  autoPlay
                  loop
                  muted
                  playsInline
                  style={{
                    width: '100%',
                    height: '240px',
                    borderRadius: '12px',
                    backgroundColor: '#000000',
                    objectFit: 'cover',
                  }}
                />
              ) : (
                <View style={styles.nativeVideoPlaceholder}>
                  <Feather name="play-circle" size={48} color="#38bdf8" />
                  <Text style={styles.nativeVideoText}>Conveyor Video Stream Active</Text>
                  <Text style={styles.nativeVideoSub}>1080p 60fps Mandi Telemetry Feed</Text>
                </View>
              )}

              {/* HUD Telemetry Badges */}
              <View style={styles.hudOverlay}>
                <View style={styles.hudBadge}>
                  <Feather name="crosshair" size={11} color="#38bdf8" style={{ marginRight: 4 }} />
                  <Text style={styles.hudBadgeText}>ChArUco Lock: 0.51 mm/px</Text>
                </View>
                <View style={styles.hudBadge}>
                  <Feather name="layers" size={11} color="#34d399" style={{ marginRight: 4 }} />
                  <Text style={styles.hudBadgeText}>24 Bulbs Segmented</Text>
                </View>
              </View>
            </View>

            {/* Mandi Assaying Metrics Bento */}
            <View style={styles.metricsGrid}>
              <View style={styles.metricCard}>
                <Text style={styles.metricLabel}>MEAN CALIBER</Text>
                <Text style={styles.metricValue}>
                  Ø 63.2 <Text style={styles.metricUnit}>mm</Text>
                </Text>
                <Text style={styles.metricSub}>Sub-mm Accuracy</Text>
              </View>

              <View style={styles.metricCard}>
                <Text style={styles.metricLabel}>APMC GRADE</Text>
                <Text style={[styles.metricValue, { color: '#059669' }]}>83.3% A</Text>
                <Text style={styles.metricSub}>20 Grade A / 3 URS</Text>
              </View>

              <View style={styles.metricCard}>
                <Text style={styles.metricLabel}>DEFECT INFERENCE</Text>
                <Text style={[styles.metricValue, { color: '#0284c7' }]}>0% Rot</Text>
                <Text style={styles.metricSub}>Dry Cured Neck</Text>
              </View>

              <View style={styles.metricCard}>
                <Text style={styles.metricLabel}>MSP VALUATION</Text>
                <Text style={[styles.metricValue, { color: '#b45309' }]}>₹2,450</Text>
                <Text style={styles.metricSub}>per Quintal</Text>
              </View>
            </View>

            {/* Explanation Note */}
            <View style={styles.noteBox}>
              <Feather name="info" size={14} color="#0284c7" style={{ marginTop: 2, marginRight: 8 }} />
              <Text style={styles.noteText}>
                This demonstration video showcases CEPA's continuous real-time instance segmentation
                and metric homography at Lasalgaon APMC yard. Even when the remote cloud container is waking
                from sleep, offline telemetry allows full inspection review below.
              </Text>
            </View>

            {/* Action Buttons */}
            <View style={styles.actionRow}>
              <AnimatedPressable
                haptic="heavy"
                onPress={() => {
                  onClose();
                  onExploreDemoLot();
                }}
                style={styles.exploreButton}
              >
                <Feather name="check-circle" size={16} color="#ffffff" style={{ marginRight: 8 }} />
                <Text style={styles.exploreButtonText}>Inspect Assayed Lot (24 Bulbs)</Text>
              </AnimatedPressable>

              <Pressable
                onPress={() => {
                  Haptics.light();
                  onClose();
                }}
                style={styles.dismissButton}
              >
                <Text style={styles.dismissButtonText}>Dismiss</Text>
              </Pressable>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.lg,
  },
  modalCard: {
    width: '100%',
    maxWidth: 580,
    maxHeight: '92%',
    backgroundColor: '#ffffff',
    borderRadius: Radius.lg,
    overflow: 'hidden',
    ...Shadows.cardHover,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(2, 132, 199, 0.1)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#0284c7',
    marginRight: 6,
  },
  liveBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#0284c7',
    letterSpacing: 0.5,
  },
  demoModeTag: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 4,
  },
  demoModeTagText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#64748b',
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0f172a',
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#f8fafc',
    justifyContent: 'center',
    alignItems: 'center',
  },
  scrollBody: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
  },
  videoWrapper: {
    width: '100%',
    borderRadius: Radius.md,
    overflow: 'hidden',
    backgroundColor: '#09090b',
    position: 'relative',
    marginBottom: Spacing.md,
  },
  nativeVideoPlaceholder: {
    height: 240,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f172a',
  },
  nativeVideoText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 10,
  },
  nativeVideoSub: {
    color: '#94a3b8',
    fontSize: 11,
    marginTop: 2,
  },
  hudOverlay: {
    position: 'absolute',
    top: 10,
    left: 10,
    right: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    pointerEvents: 'none',
  },
  hudBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.82)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  hudBadgeText: {
    color: '#f8fafc',
    fontSize: 10,
    fontWeight: '600',
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: Spacing.md,
  },
  metricCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: '#f8fafc',
    borderRadius: Radius.sm,
    padding: 10,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  metricLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#64748b',
    letterSpacing: 0.5,
  },
  metricValue: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0f172a',
    marginTop: 2,
  },
  metricUnit: {
    fontSize: 12,
    fontWeight: '500',
    color: '#64748b',
  },
  metricSub: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
  },
  noteBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#f0f9ff',
    borderWidth: 1,
    borderColor: '#bae6fd',
    borderRadius: Radius.sm,
    padding: 10,
    marginBottom: Spacing.md,
  },
  noteText: {
    flex: 1,
    fontSize: 11,
    color: '#0369a1',
    lineHeight: 16,
  },
  actionRow: {
    gap: 8,
  },
  exploreButton: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0f172a',
    borderRadius: Radius.sm,
    paddingVertical: 12,
    paddingHorizontal: Spacing.md,
  },
  exploreButtonText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
  },
  dismissButton: {
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 10,
  },
  dismissButtonText: {
    color: '#64748b',
    fontSize: 12,
    fontWeight: '600',
  },
});
