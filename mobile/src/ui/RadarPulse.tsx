import React, { useEffect, useRef } from 'react';
import { Animated, StyleSheet, View } from 'react-native';
import { Colors } from './Theme';

interface RadarPulseProps {
  size?: number;
  color?: string;
  active?: boolean;
}

export const RadarPulse: React.FC<RadarPulseProps> = ({
  size = 48,
  color = Colors.accent,
  active = true,
}) => {
  const pulseAnim1 = useRef(new Animated.Value(0)).current;
  const pulseAnim2 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!active) return;

    const createRingAnimation = (anim: Animated.Value, delay: number) => {
      return Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(anim, {
            toValue: 1,
            duration: 1800,
            useNativeDriver: true,
          }),
          Animated.timing(anim, {
            toValue: 0,
            duration: 0,
            useNativeDriver: true,
          }),
        ])
      );
    };

    const anim1 = createRingAnimation(pulseAnim1, 0);
    const anim2 = createRingAnimation(pulseAnim2, 900);

    anim1.start();
    anim2.start();

    return () => {
      anim1.stop();
      anim2.stop();
    };
  }, [active, pulseAnim1, pulseAnim2]);

  const ringStyle = (anim: Animated.Value) => ({
    width: size,
    height: size,
    borderRadius: size / 2,
    borderColor: color,
    borderWidth: 1.5,
    position: 'absolute' as const,
    opacity: anim.interpolate({
      inputRange: [0, 0.7, 1],
      outputRange: [0.8, 0.3, 0],
    }),
    transform: [
      {
        scale: anim.interpolate({
          inputRange: [0, 1],
          outputRange: [0.6, 2.2],
        }),
      },
    ],
  });

  return (
    <View style={[styles.container, { width: size, height: size }]}>
      {active && <Animated.View style={ringStyle(pulseAnim1)} />}
      {active && <Animated.View style={ringStyle(pulseAnim2)} />}
      <View
        style={[
          styles.centerDot,
          {
            width: size * 0.35,
            height: size * 0.35,
            borderRadius: (size * 0.35) / 2,
            backgroundColor: color,
            shadowColor: color,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  centerDot: {},
});
