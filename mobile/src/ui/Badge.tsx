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
          label: 'Grade A',
          color: Colors.gradeA,
          bg: Colors.gradeABg,
          borderColor: Colors.gradeABorder,
        };
      case 'URS':
        return {
          label: 'URS',
          color: Colors.urs,
          bg: Colors.ursBg,
          borderColor: Colors.ursBorder,
        };
      case 'REJECTED':
        return {
          label: 'Rejected',
          color: Colors.reject,
          bg: Colors.rejectBg,
          borderColor: Colors.rejectBorder,
        };
      case 'FINALIZED':
        return {
          label: 'Certified',
          color: Colors.gradeA,
          bg: Colors.gradeABg,
          borderColor: Colors.gradeABorder,
        };
      case 'PROCESSING':
        return {
          label: 'Processing',
          color: Colors.accent,
          bg: Colors.accentSubtle,
          borderColor: Colors.border,
        };
      default:
        return {
          label: grade ? grade.replace(/_/g, ' ') : 'Review',
          color: Colors.review,
          bg: Colors.reviewBg,
          borderColor: Colors.reviewBorder,
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
          paddingHorizontal: isSmall ? 7 : isLarge ? 12 : 9,
          paddingVertical: isSmall ? 2 : isLarge ? 5 : 3,
        },
        style,
      ]}
    >
      <View
        style={[
          styles.dot,
          {
            backgroundColor: config.color,
            width: isSmall ? 5 : isLarge ? 7 : 6,
            height: isSmall ? 5 : isLarge ? 7 : 6,
            borderRadius: isSmall ? 2.5 : isLarge ? 3.5 : 3,
          },
        ]}
      />
      <Text
        style={[
          styles.label,
          {
            color: config.color,
            fontSize: isSmall ? 10 : isLarge ? 12 : 11,
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
        return Colors.textSecondary;
      case 'JUMBO':
        return Colors.accent;
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
          borderColor: Colors.border,
          backgroundColor: Colors.cardBgElevated,
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
    // No neon glow halos
  },
  label: {
    fontWeight: '600',
    letterSpacing: 0.2,
  },
  sizeBadge: {
    borderWidth: 1,
    borderRadius: Radius.xs,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  sizeLabel: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
});
