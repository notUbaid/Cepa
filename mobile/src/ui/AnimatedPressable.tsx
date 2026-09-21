import React, { useRef } from 'react';
import {
  Animated,
  GestureResponderEvent,
  Platform,
  Pressable,
  StyleProp,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { Haptics } from './Haptics';

interface AnimatedPressableProps {
  children: React.ReactNode;
  onPress?: (event: GestureResponderEvent) => void;
  onLongPress?: (event: GestureResponderEvent) => void;
  style?: StyleProp<ViewStyle>;
  disabled?: boolean;
  haptic?: 'light' | 'medium' | 'heavy' | 'selection' | 'none';
  scaleTo?: number;
  testID?: string;
}

export const AnimatedPressable: React.FC<AnimatedPressableProps> = ({
  children,
  onPress,
  onLongPress,
  style,
  disabled = false,
  haptic = 'light',
  scaleTo = 0.96,
  testID,
}) => {
  const scaleAnim = useRef(new Animated.Value(1)).current;

  // Flatten style so flex and layout styles properly propagate to the outer Pressable
  const flattened = (StyleSheet.flatten(style) || {}) as ViewStyle;
  const pressableStyle: ViewStyle = {};
  if (flattened.flex !== undefined) pressableStyle.flex = flattened.flex;
  if (flattened.width !== undefined) pressableStyle.width = flattened.width;
  if (flattened.alignSelf !== undefined) pressableStyle.alignSelf = flattened.alignSelf;

  const handlePressIn = () => {
    if (disabled) return;
    Animated.spring(scaleAnim, {
      toValue: scaleTo,
      useNativeDriver: Platform.OS !== 'web',
      speed: 35,
      bounciness: 4,
    }).start();
  };

  const handlePressOut = () => {
    if (disabled) return;
    Animated.spring(scaleAnim, {
      toValue: 1,
      useNativeDriver: Platform.OS !== 'web',
      speed: 25,
      bounciness: 6,
    }).start();
  };

  const handlePress = (e: GestureResponderEvent) => {
    if (disabled) return;
    if (haptic === 'light') Haptics.light();
    else if (haptic === 'medium') Haptics.medium();
    else if (haptic === 'heavy') Haptics.heavy();
    else if (haptic === 'selection') Haptics.selection();
    onPress?.(e);
  };

  return (
    <Pressable
      testID={testID}
      disabled={disabled}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      onPress={handlePress}
      onLongPress={onLongPress}
      style={pressableStyle}
    >
      <Animated.View
        style={[
          style,
          {
            transform: [{ scale: scaleAnim }],
            opacity: disabled ? 0.5 : 1,
          },
        ]}
      >
        {children}
      </Animated.View>
    </Pressable>
  );
};
