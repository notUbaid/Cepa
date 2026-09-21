import React, { useEffect, useRef } from 'react';
import { Animated, Platform, StyleSheet, Text, View } from 'react-native';
import { AnimatedPressable, Colors, Haptics, Radius, Spacing, Typography } from '../ui';

interface HeaderProps {
  serverConnected?: boolean;
  policyVersion?: string;
  isMockActive?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  serverConnected = true,
  policyVersion = 'DEMO_ASSUMPTION_v1',
  isMockActive = false,
}) => {
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!serverConnected) return;

    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.35,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    );
    pulse.start();

    return () => pulse.stop();
  }, [serverConnected, pulseAnim]);

  return (
    <View style={styles.container}>
      {/* Brand & Connection Row */}
      <View style={styles.topRow}>
        <View style={styles.brandRow}>
          <View style={styles.logoBadge}>
            <Text style={styles.logoIcon}>🧅</Text>
          </View>
          <View>
            <View style={styles.titleRow}>
              <Text style={styles.brandTitle}>CEPA</Text>
              <View style={styles.sihTag}>
                <Text style={styles.sihTagText}>SIH26031</Text>
              </View>
            </View>
            <Text style={styles.subtitle}>Autonomous Onion Mandi Inspection</Text>
          </View>
        </View>

        <AnimatedPressable
          haptic="selection"
          style={[
            styles.statusIndicator,
            {
              backgroundColor: serverConnected
                ? Colors.gradeABg
                : Colors.rejectBg,
              borderColor: serverConnected
                ? 'rgba(16, 185, 129, 0.4)'
                : 'rgba(239, 68, 68, 0.4)',
            },
          ]}
        >
          <Animated.View
            style={[
              styles.dot,
              {
                backgroundColor: serverConnected ? Colors.gradeA : Colors.reject,
                opacity: serverConnected ? pulseAnim : 1,
              },
            ]}
          />
          <Text
            style={[
              styles.statusText,
              { color: serverConnected ? Colors.gradeA : Colors.reject },
            ]}
          >
            {serverConnected ? 'ONLINE' : 'OFFLINE'}
          </Text>
        </AnimatedPressable>
      </View>

      {/* Badges Strip */}
      <View style={styles.badgesRow}>
        <View style={styles.policyBadge}>
          <Text style={styles.policyLabel}>Standard:</Text>
          <Text style={styles.policyText}>
            {policyVersion.replace('BIS_IS_17912_2022', 'BIS IS 17912:2022')}
          </Text>
        </View>

        {isMockActive ? (
          <View style={styles.mockBadge}>
            <Text style={styles.mockText}>MOCK CLASSIFIER</Text>
          </View>
        ) : (
          <View style={styles.realModelBadge}>
            <Text style={styles.realModelText}>⚡ MobileNetV3 (98.8% Acc)</Text>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bg,
    paddingTop: Platform.OS === 'android' ? 38 : 14,
    paddingBottom: Spacing.md,
    paddingHorizontal: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  logoBadge: {
    width: 38,
    height: 38,
    borderRadius: Radius.md,
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoIcon: {
    fontSize: 20,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandTitle: {
    ...Typography.title1,
    color: Colors.text,
    letterSpacing: 0.5,
  },
  sihTag: {
    backgroundColor: Colors.accentSubtle,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.xs,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  sihTagText: {
    fontSize: 9,
    fontFamily: 'monospace',
    color: Colors.accent,
    fontWeight: '700',
  },
  subtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 1,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radius.pill,
    borderWidth: 1,
    gap: 6,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  badgesRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.sm,
    gap: Spacing.sm,
    flexWrap: 'wrap',
  },
  policyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    gap: 4,
  },
  policyLabel: {
    fontSize: 10,
    color: Colors.textDim,
  },
  policyText: {
    fontSize: 10,
    color: Colors.accent,
    fontWeight: '600',
    fontFamily: 'monospace',
  },
  realModelBadge: {
    backgroundColor: Colors.gradeABg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.35)',
  },
  realModelText: {
    fontSize: 10,
    color: Colors.gradeA,
    fontWeight: '600',
  },
  mockBadge: {
    backgroundColor: Colors.rejectBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
  },
  mockText: {
    fontSize: 9,
    color: Colors.reject,
    fontWeight: '700',
  },
});
