import React, { useEffect, useRef } from 'react';
import { Animated, DimensionValue, StyleSheet, View, ViewStyle } from 'react-native';
import { Colors, Radius, Spacing } from './Theme';

interface SkeletonBoxProps {
  width?: DimensionValue;
  height?: DimensionValue;
  borderRadius?: number;
  style?: ViewStyle;
}

export const SkeletonBox: React.FC<SkeletonBoxProps> = ({
  width = '100%',
  height = 20,
  borderRadius = Radius.sm,
  style,
}) => {
  const pulseAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 900,
          useNativeDriver: false,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0,
          duration: 900,
          useNativeDriver: false,
        }),
      ])
    );
    animation.start();
    return () => animation.stop();
  }, [pulseAnim]);

  const backgroundColor = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [Colors.skeletonBase, Colors.skeletonHighlight],
  });

  return (
    <Animated.View
      style={[
        styles.base,
        {
          width,
          height,
          borderRadius,
          backgroundColor,
        },
        style,
      ]}
    />
  );
};

export const SkeletonCircle: React.FC<{ size: number; style?: ViewStyle }> = ({
  size,
  style,
}) => {
  return (
    <SkeletonBox
      width={size}
      height={size}
      borderRadius={size / 2}
      style={style}
    />
  );
};

export const SkeletonText: React.FC<{
  lines?: number;
  lineHeight?: number;
  lastLineWidth?: DimensionValue;
  style?: ViewStyle;
}> = ({ lines = 2, lineHeight = 14, lastLineWidth = '60%', style }) => {
  return (
    <View style={style}>
      {Array.from({ length: lines }).map((_, idx) => (
        <SkeletonBox
          key={idx}
          width={idx === lines - 1 && lines > 1 ? lastLineWidth : '100%'}
          height={lineHeight}
          style={{ marginBottom: idx < lines - 1 ? 8 : 0 }}
        />
      ))}
    </View>
  );
};

export const SkeletonKpiCard: React.FC = () => {
  return (
    <View style={styles.kpiCard}>
      <SkeletonBox width={50} height={28} style={{ marginBottom: 6 }} />
      <SkeletonBox width={36} height={14} style={{ marginBottom: 6 }} />
      <SkeletonBox width={60} height={12} />
    </View>
  );
};

export const SkeletonOnionCard: React.FC = () => {
  return (
    <View style={styles.onionCard}>
      <SkeletonBox width="100%" height={110} borderRadius={Radius.md} style={{ marginBottom: 8 }} />
      <SkeletonBox width="70%" height={14} style={{ marginBottom: 6 }} />
      <SkeletonBox width="50%" height={12} style={{ marginBottom: 8 }} />
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <SkeletonBox width={45} height={16} borderRadius={Radius.xs} />
        <SkeletonBox width={45} height={16} borderRadius={Radius.xs} />
      </View>
    </View>
  );
};

export const SkeletonInspectionRow: React.FC = () => {
  return (
    <View style={styles.inspectionRow}>
      <View style={{ flex: 1, marginRight: Spacing.md }}>
        <SkeletonBox width="60%" height={16} style={{ marginBottom: 8 }} />
        <SkeletonBox width="85%" height={12} style={{ marginBottom: 6 }} />
        <SkeletonBox width="40%" height={10} />
      </View>
      <SkeletonBox width={70} height={24} borderRadius={Radius.xs} />
    </View>
  );
};

const styles = StyleSheet.create({
  base: {
    overflow: 'hidden',
  },
  kpiCard: {
    flex: 1,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    alignItems: 'center',
    marginHorizontal: Spacing.xs,
  },
  onionCard: {
    flex: 1,
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    margin: Spacing.xs,
  },
  inspectionRow: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    marginBottom: Spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});
