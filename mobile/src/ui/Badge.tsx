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
          color: Colors.text,
          bg: Colors.cardBgElevated,
          borderColor: Colors.border,
        };
      case 'URS':
        return {
          label: 'URS',
          color: Colors.urs,
          bg: Colors.cardBgElevated,
          borderColor: Colors.border,
        };
      case 'REJECTED':
        return {
          label: 'Rejected',
          color: Colors.reject,
          bg: Colors.cardBgElevated,
          borderColor: Colors.border,
        };
      case 'FINALIZED':
        return {
          label: 'Certified',
          color: Colors.text,
          bg: Colors.cardBgElevated,
          borderColor: Colors.border,
        };
      case 'PROCESSING':
        return {
          label: 'Processing',
          color: Colors.textSecondary,
          bg: Colors.cardBgElevated,
          borderColor: Colors.border,
        };
      default:
        return {
          label: grade ? grade.replace(/_/g, ' ') : 'Review',
          color: Colors.review,
          bg: Colors.cardBgElevated,
          borderColor: Colors.border,
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
          paddingHorizontal: isSmall ? 6 : isLarge ? 10 : 8,
          paddingVertical: isSmall ? 2 : isLarge ? 4 : 2.5,
        },
        style,
      ]}
    >
      <View
        style={[
          styles.dot,
          {
            backgroundColor: config.color,
            width: isSmall ? 4 : isLarge ? 6 : 5,
            height: isSmall ? 4 : isLarge ? 6 : 5,
            borderRadius: isSmall ? 2 : isLarge ? 3 : 2.5,
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
        return Colors.text;
      case 'MADHYAM':
        return Colors.textSecondary;
      case 'JUMBO':
        return Colors.text;
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
    borderRadius: Radius.xs,
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
