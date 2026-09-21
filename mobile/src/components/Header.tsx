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
  policyVersion = 'BIS_IS_17912_2022',
  isMockActive = false,
}) => {
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!serverConnected) return;

    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.4,
          duration: 1200,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1200,
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
          <View style={styles.logoMark}>
            <Text style={styles.logoLetter}>C</Text>
          </View>
          <View>
            <View style={styles.titleRow}>
              <Text style={styles.brandTitle}>CEPA</Text>
              <View style={styles.standardPill}>
                <Text style={styles.standardText}>APMC Mandi</Text>
              </View>
            </View>
            <Text style={styles.subtitle}>Onion Quality & Procurement</Text>
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
                ? Colors.gradeABorder
                : Colors.rejectBorder,
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
            {serverConnected ? 'Online' : 'Offline'}
          </Text>
        </AnimatedPressable>
      </View>

      {/* Sub-header strip: Standard & Center info */}
      <View style={styles.subStrip}>
        <Text style={styles.subStripText}>
          Grading Standard: {policyVersion.includes('BIS') ? 'BIS IS 17912:2022' : 'NAFED FAQ Standard'}
        </Text>
        <Text style={styles.subStripDivider}>•</Text>
        <Text style={styles.subStripText}>Optical Caliper</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.cardBg,
    paddingTop: Platform.OS === 'android' ? 40 : 16,
    paddingBottom: Spacing.sm,
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
  logoMark: {
    width: 36,
    height: 36,
    borderRadius: Radius.sm,
    backgroundColor: Colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoLetter: {
    fontSize: 18,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -0.5,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandTitle: {
    ...Typography.title2,
    fontSize: 17,
    color: Colors.text,
    letterSpacing: 0.5,
    fontWeight: '800',
  },
  standardPill: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.xs,
    paddingHorizontal: 6,
    paddingVertical: 1,
  },
  standardText: {
    fontSize: 10,
    color: Colors.textSecondary,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 1,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: Radius.pill,
    borderWidth: 1,
    gap: 6,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  subStrip: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
    gap: 6,
  },
  subStripText: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  subStripDivider: {
    fontSize: 10,
    color: Colors.borderHighlight,
  },
});
