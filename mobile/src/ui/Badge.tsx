import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Colors, Radius, Spacing } from './Theme';

interface GradeBadgeProps {
  grade?: string | null;
  size?: 'sm' | 'md' | 'lg';
  style?: ViewStyle;
}

export const GradeBadge: React.FC<GradeBadgeProps> = ({
  grade,
  size = 'md',
  style,
}) => {
  const getGradeConfig = () => {
    switch (grade) {
      case 'GRADE_A':
        return {
          label: 'GRADE A',
          color: Colors.gradeA,
          bg: Colors.gradeABg,
          borderColor: 'rgba(16, 185, 129, 0.35)',
        };
      case 'URS':
        return {
          label: 'URS',
          color: Colors.urs,
          bg: Colors.ursBg,
          borderColor: 'rgba(245, 158, 11, 0.35)',
        };
      case 'REJECTED':
        return {
          label: 'REJECTED',
          color: Colors.reject,
          bg: Colors.rejectBg,
          borderColor: 'rgba(239, 68, 68, 0.35)',
        };
      case 'FINALIZED':
        return {
          label: 'FINALIZED',
          color: Colors.gradeA,
          bg: Colors.gradeABg,
          borderColor: 'rgba(16, 185, 129, 0.35)',
        };
      case 'PROCESSING':
        return {
          label: 'PROCESSING',
          color: Colors.accent,
          bg: Colors.accentSubtle,
          borderColor: 'rgba(56, 189, 248, 0.35)',
        };
      default:
        return {
          label: grade || 'REVIEW',
          color: Colors.review,
          bg: Colors.reviewBg,
          borderColor: 'rgba(139, 92, 246, 0.35)',
        };
    }
  };

  const config = getGradeConfig();

  const isSmall = size === 'sm';
  const isLarge = size === 'lg';

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: config.bg,
          borderColor: config.borderColor,
          paddingHorizontal: isSmall ? 6 : isLarge ? 12 : 8,
          paddingVertical: isSmall ? 2 : isLarge ? 6 : 4,
        },
        style,
      ]}
    >
      <View
        style={[
          styles.dot,
          {
            backgroundColor: config.color,
            shadowColor: config.color,
            width: isSmall ? 5 : isLarge ? 8 : 6,
            height: isSmall ? 5 : isLarge ? 8 : 6,
            borderRadius: isSmall ? 2.5 : isLarge ? 4 : 3,
          },
        ]}
      />
      <Text
        style={[
          styles.label,
          {
            color: config.color,
            fontSize: isSmall ? 10 : isLarge ? 13 : 11,
          },
        ]}
      >
        {config.label}
      </Text>
    </View>
  );
};

export const SizeTierBadge: React.FC<{ tier?: string | null; style?: ViewStyle }> = ({
  tier,
  style,
}) => {
  const getTierColor = () => {
    switch (tier?.toUpperCase()) {
      case 'SUPER':
        return Colors.gradeA;
      case 'MADHYAM':
        return Colors.accent;
      case 'JUMBO':
        return '#a855f7';
      case 'GOLI':
        return Colors.urs;
      default:
        return Colors.textMuted;
    }
  };

  const color = getTierColor();

  return (
    <View
      style={[
        styles.sizeBadge,
        {
          borderColor: color,
        },
        style,
      ]}
    >
      <Text style={[styles.sizeLabel, { color }]}>
        {tier ? tier.toUpperCase() : 'STANDARD'}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: Radius.pill,
    borderWidth: 1,
    gap: 5,
  },
  dot: {
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 4,
    elevation: 3,
  },
  label: {
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  sizeBadge: {
    borderWidth: 1,
    borderRadius: Radius.sm,
    paddingHorizontal: 6,
    paddingVertical: 2,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
  },
  sizeLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
});
