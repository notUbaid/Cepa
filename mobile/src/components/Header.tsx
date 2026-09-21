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
              <Text style={styles.brandSubtitleInline}>• Mandi Protocol</Text>
            </View>
            <Text style={styles.subtitle}>Onion Quality & Procurement</Text>
          </View>
        </View>

        <View style={styles.statusIndicator}>
          <Animated.View
            style={[
              styles.dot,
              {
                backgroundColor: serverConnected ? Colors.textSecondary : Colors.reject,
                opacity: serverConnected ? pulseAnim : 1,
              },
            ]}
          />
          <Text style={styles.statusText}>
            {serverConnected ? 'Online' : 'Offline'}
          </Text>
        </View>
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
  brandSubtitleInline: {
    fontSize: 11,
    color: Colors.textMuted,
    fontWeight: '500',
  },
  subtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 1,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 4,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '500',
    color: Colors.textSecondary,
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
