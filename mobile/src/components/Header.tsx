import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Image,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Colors, Radius, Shadows, Spacing, Typography } from '../ui';

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
          {/* Bespoke Cepa Logo Emblem */}
          <View style={styles.logoWrapper}>
            <Image
              source={require('../../assets/logo.png')}
              style={styles.logoImage}
              resizeMode="contain"
            />
          </View>
          <View>
            <View style={styles.titleRow}>
              <Text style={styles.brandTitle}>CEPA</Text>
              <View style={styles.protocolBadge}>
                <Text style={styles.protocolBadgeText}>NAFED / APMC PROTOCOL</Text>
              </View>
            </View>
            <Text style={styles.subtitle}>Onion Quality & Optical Caliper Appraisal</Text>
          </View>
        </View>

        <View style={[styles.statusIndicator, serverConnected ? styles.statusIndicatorOnline : styles.statusIndicatorOffline]}>
          <Animated.View
            style={[
              styles.dot,
              {
                backgroundColor: serverConnected ? '#10b981' : Colors.reject,
                opacity: serverConnected ? pulseAnim : 1,
              },
            ]}
          />
          <Text style={[styles.statusText, serverConnected ? styles.statusTextOnline : styles.statusTextOffline]}>
            {serverConnected ? 'System Live' : 'Offline'}
          </Text>
        </View>
      </View>

      {/* Sub-header strip: Standard & Center info chips */}
      <View style={styles.subStrip}>
        <View style={styles.stripChip}>
          <Text style={styles.stripChipTag}>STANDARD</Text>
          <Text style={styles.stripChipText}>
            {policyVersion.includes('BIS') ? 'BIS IS 17912:2022' : 'NAFED FAQ Standard'}
          </Text>
        </View>
        <View style={styles.stripChip}>
          <Text style={styles.stripChipTag}>CALIPER</Text>
          <Text style={styles.stripChipText}>Sub-mm Optical Engine</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#ffffff',
    paddingTop: Platform.OS === 'android' ? 40 : 14,
    paddingBottom: Spacing.sm,
    paddingHorizontal: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e2db',
    ...Shadows.sm,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  logoWrapper: {
    width: 42,
    height: 42,
    borderRadius: 10,
    backgroundColor: '#0c0c0e',
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: 'rgba(16, 185, 129, 0.45)',
    justifyContent: 'center',
    alignItems: 'center',
    ...Shadows.glowGreen,
  },
  logoImage: {
    width: 38,
    height: 38,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  brandTitle: {
    ...Typography.title2,
    fontSize: 18,
    color: '#0c0c0e',
    letterSpacing: 0.5,
    fontWeight: '800',
  },
  protocolBadge: {
    backgroundColor: '#ecfdf5',
    paddingHorizontal: 7,
    paddingVertical: 2.5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#a7f3d0',
  },
  protocolBadgeText: {
    fontSize: 9,
    fontWeight: '800',
    color: '#047857',
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
    fontWeight: '500',
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
  },
  statusIndicatorOnline: {
    backgroundColor: '#ecfdf5',
    borderColor: '#a7f3d0',
  },
  statusIndicatorOffline: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
  },
  statusTextOnline: {
    color: '#047857',
  },
  statusTextOffline: {
    color: '#b91c1c',
  },
  subStrip: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
    gap: 8,
  },
  stripChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#f8fafc',
    paddingHorizontal: 8,
    paddingVertical: 3.5,
    borderRadius: 5,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  stripChipTag: {
    fontSize: 9,
    fontWeight: '800',
    color: '#0284c7',
    letterSpacing: 0.5,
  },
  stripChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#334155',
  },
});
