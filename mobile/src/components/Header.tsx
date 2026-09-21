import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

interface HeaderProps {
  serverConnected?: boolean;
  policyVersion?: string;
  isMockActive?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  serverConnected = true,
  policyVersion = 'DEMO_ASSUMPTION_v1',
  isMockActive = true,
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.topRow}>
        <View>
          <Text style={styles.brandTitle}>CEPA</Text>
          <Text style={styles.subtitle}>Onion Inspection & Grading System (SIH26031)</Text>
        </View>
        <View style={styles.statusIndicator}>
          <View
            style={[
              styles.dot,
              { backgroundColor: serverConnected ? '#2ecc71' : '#e74c3c' },
            ]}
          />
          <Text style={styles.statusText}>
            {serverConnected ? 'ONLINE' : 'OFFLINE'}
          </Text>
        </View>
      </View>

      <View style={styles.badgesRow}>
        <View style={styles.policyBadge}>
          <Text style={styles.policyText}>Policy: {policyVersion}</Text>
        </View>
        {isMockActive && (
          <View style={styles.mockBadge}>
            <Text style={styles.mockText}>MOCK DEFECT CLASSIFIER</Text>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#1b263b',
    paddingTop: 45,
    paddingBottom: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#2d3748',
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brandTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#f8f9fa',
    letterSpacing: 1,
  },
  subtitle: {
    fontSize: 11,
    color: '#a0aec0',
    marginTop: 2,
  },
  statusIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.08)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#e2e8f0',
  },
  badgesRow: {
    flexDirection: 'row',
    marginTop: 8,
    gap: 8,
  },
  policyBadge: {
    backgroundColor: '#2b3a4a',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  policyText: {
    fontSize: 10,
    color: '#90cdf4',
    fontWeight: '600',
  },
  mockBadge: {
    backgroundColor: 'rgba(231, 76, 60, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#e74c3c',
  },
  mockText: {
    fontSize: 9,
    color: '#ff7675',
    fontWeight: '700',
  },
});
