import React, { useEffect, useRef } from 'react';
import {
  Animated,
  Image,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { getApiBaseUrl } from '../config';
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
              <View style={styles.mandiPill}>
                <Text style={styles.mandiPillText}>APMC TERMINAL</Text>
              </View>
            </View>
            <Text style={styles.subtitle}>Autonomous Optical & AI Quality Suite</Text>
          </View>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Backend Connection Status"
          accessibilityHint="Tap to view backend endpoint and server status"
          onPress={() => {
            const endpoint = getApiBaseUrl();
            alert(`Cepa Grading Engine:\nStatus: ${serverConnected ? 'ONLINE (Connected)' : 'OFFLINE (Connecting)'}\nEndpoint: ${endpoint}`);
          }}
          style={[
            styles.statusIndicator,
            serverConnected ? styles.statusIndicatorOnline : styles.statusIndicatorOffline,
          ]}
        >
          <Animated.View
            style={[
              styles.dot,
              {
                backgroundColor: serverConnected ? '#059669' : '#dc2626',
                opacity: serverConnected ? pulseAnim : 1,
              },
            ]}
          />
          <Text
            style={[
              styles.statusText,
              serverConnected ? styles.statusTextOnline : styles.statusTextOffline,
            ]}
          >
            {serverConnected ? 'ONLINE' : 'OFFLINE'}
          </Text>
        </Pressable>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#ffffff',
    paddingTop: Spacing.sm,
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
    fontSize: 17,
    color: '#0f172a',
    letterSpacing: 1.8,
    fontWeight: '800',
  },
  mandiPill: {
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  mandiPillText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#475569',
    letterSpacing: 0.8,
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
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
  },
  statusIndicatorOnline: {
    backgroundColor: '#f0fdf4',
    borderColor: '#bbf7d0',
  },
  statusIndicatorOffline: {
    backgroundColor: '#fef2f2',
    borderColor: '#fecaca',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  statusTextOnline: {
    color: '#059669',
  },
  statusTextOffline: {
    color: '#dc2626',
  },
});
