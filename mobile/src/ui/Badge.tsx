import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { Colors, Radius, Spacing } from './Theme';

interface GradeBadgeProps {
  grade?: string | null;
  rejectionReasons?: string[];
  size?: 'sm' | 'md' | 'lg';
  style?: ViewStyle;
}

export const GradeBadge: React.FC<GradeBadgeProps> = ({
  grade,
  rejectionReasons,
  size = 'md',
  style,
}) => {
  const getGradeConfig = () => {
    switch (grade?.toUpperCase()) {
      case 'GRADE_A':
        return {
          label: 'Grade A',
          color: Colors.gradeA,
          bg: Colors.gradeABg,
          borderColor: Colors.gradeABorder,
        };
      case 'URS':
        return {
          label: 'URS Standard',
          color: Colors.urs,
          bg: Colors.ursBg,
          borderColor: Colors.ursBorder,
        };
      case 'REJECTED':
      case 'REJECT':
        if (rejectionReasons?.includes('OVERSIZED')) {
          return {
            label: 'Oversized (>70mm)',
            color: '#7c3aed',
            bg: '#f5f3ff',
            borderColor: '#ddd6fe',
          };
        }
        if (rejectionReasons?.includes('UNDERSIZED')) {
          return {
            label: 'Undersized (<35mm)',
            color: '#d97706',
            bg: '#fffbeb',
            borderColor: '#fde68a',
          };
        }
        if (rejectionReasons?.includes('DOUBLE_BULB')) {
          return {
            label: 'Double Bulb',
            color: '#ea580c',
            bg: '#fff7ed',
            borderColor: '#fed7aa',
          };
        }
        if (rejectionReasons?.includes('ROTTEN')) {
          return {
            label: 'Rotten',
            color: Colors.reject,
            bg: Colors.rejectBg,
            borderColor: Colors.rejectBorder,
          };
        }
        if (rejectionReasons?.includes('SPROUTED')) {
          return {
            label: 'Sprouted',
            color: Colors.reject,
            bg: Colors.rejectBg,
            borderColor: Colors.rejectBorder,
          };
        }
        return {
          label: 'Non-Procurement',
          color: Colors.reject,
          bg: Colors.rejectBg,
          borderColor: Colors.rejectBorder,
        };
      case 'FINALIZED':
        return {
          label: 'Certified Lot',
          color: Colors.gradeA,
          bg: Colors.gradeABg,
          borderColor: Colors.gradeABorder,
        };
      case 'PROCESSING':
        return {
          label: 'Processing',
          color: Colors.review,
          bg: Colors.reviewBg,
          borderColor: Colors.reviewBorder,
        };
      case 'DRAFT':
        return {
          label: 'Draft Lot',
          color: '#475569',
          bg: '#f1f5f9',
          borderColor: '#cbd5e1',
        };
      default:
        return {
          label: grade ? grade.replace(/_/g, ' ') : 'Pending Review',
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
          paddingVertical: isSmall ? 3 : isLarge ? 5 : 3.5,
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
            borderRadius: 4,
          },
        ]}
      />
      <Text
        style={[
          styles.label,
          {
            color: config.color,
            fontSize: isSmall ? 10.5 : isLarge ? 12.5 : 11.5,
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
  const getTierConfig = () => {
    switch (tier?.toUpperCase()) {
      case 'SUPER':
        return { color: '#047857', bg: '#ecfdf5', border: '#a7f3d0' };
      case 'MADHYAM':
        return { color: '#0369a1', bg: '#f0f9ff', border: '#bae6fd' };
      case 'JUMBO':
        return { color: '#6d28d9', bg: '#f5f3ff', border: '#ddd6fe' };
      case 'GOLI':
        return { color: '#b45309', bg: '#fffbeb', border: '#fde68a' };
      default:
        return { color: '#475569', bg: '#f1f5f9', border: '#e2e8f0' };
    }
  };

  const config = getTierConfig();

  return (
    <View
      style={[
        styles.sizeBadge,
        {
          borderColor: config.border,
          backgroundColor: config.bg,
        },
        style,
      ]}
    >
      <Text style={[styles.sizeLabel, { color: config.color }]}>
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
