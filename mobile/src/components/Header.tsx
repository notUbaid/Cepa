import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Image,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Colors, Radius, Spacing, Typography } from '../ui';

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
                <Text style={styles.protocolBadgeText}>MANDI PROTOCOL</Text>
              </View>
            </View>
            <Text style={styles.subtitle}>Onion Quality & Optical Caliper Appraisal</Text>
          </View>
        </View>

        <View style={styles.statusIndicator}>
          <Animated.View
            style={[
              styles.dot,
              {
                backgroundColor: serverConnected ? '#10b981' : Colors.reject,
                opacity: serverConnected ? pulseAnim : 1,
              },
            ]}
          />
          <Text style={[styles.statusText, serverConnected && { color: '#047857' }]}>
            {serverConnected ? 'System Online' : 'Offline'}
          </Text>
        </View>
      </View>

      {/* Sub-header strip: Standard & Center info */}
      <View style={styles.subStrip}>
        <View style={styles.stripLeft}>
          <Text style={styles.subStripTag}>STANDARD</Text>
          <Text style={styles.subStripText}>
            {policyVersion.includes('BIS') ? 'BIS IS 17912:2022' : 'NAFED FAQ Standard'}
          </Text>
        </View>
        <View style={styles.stripRight}>
          <Text style={styles.subStripTag}>ENGINE</Text>
          <Text style={styles.subStripText}>Sub-mm Optical Caliper</Text>
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
    borderBottomColor: '#e7e5e4',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 2,
    elevation: 1,
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
    width: 38,
    height: 38,
    borderRadius: 8,
    backgroundColor: '#0c0c0e',
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoImage: {
    width: 36,
    height: 36,
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
    backgroundColor: '#f4f3ef',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#e7e5e4',
  },
  protocolBadgeText: {
    fontSize: 9.5,
    fontWeight: '700',
    color: '#52525b',
    letterSpacing: 0.4,
  },
  subtitle: {
    fontSize: 11,
    color: '#71717a',
    marginTop: 2,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#f4f3ef',
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#e7e5e4',
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#52525b',
  },
  subStrip: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 6,
    borderTopWidth: 1,
    borderTopColor: '#f5f5f4',
  },
  stripLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  stripRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  subStripTag: {
    fontSize: 9,
    fontWeight: '700',
    color: '#a1a1aa',
    letterSpacing: 0.5,
  },
  subStripText: {
    fontSize: 11,
    fontWeight: '500',
    color: '#44403c',
  },
});
