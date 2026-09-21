import React, { useRef, useState } from 'react';
import {
  Animated,
  Image,
  ImageResizeMode,
  ImageSourcePropType,
  ImageStyle,
  StyleSheet,
  Text,
  View,
  ViewStyle,
} from 'react-native';
import { SkeletonBox } from './Skeleton';
import { Colors, Radius } from './Theme';

interface LazyImageProps {
  source: ImageSourcePropType | { uri: string | null | undefined };
  style?: ImageStyle;
  containerStyle?: ViewStyle;
  resizeMode?: ImageResizeMode;
  fallbackText?: string;
  borderRadius?: number;
}

export const LazyImage: React.FC<LazyImageProps> = ({
  source,
  style,
  containerStyle,
  resizeMode = 'cover',
  fallbackText = 'C',
  borderRadius = Radius.md,
}) => {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const opacityAnim = useRef(new Animated.Value(0)).current;

  const handleLoad = () => {
    setLoaded(true);
    Animated.timing(opacityAnim, {
      toValue: 1,
      duration: 320,
      useNativeDriver: true,
    }).start();
  };

  const handleError = () => {
    setError(true);
    setLoaded(true);
  };

  const isUriEmpty =
    typeof source === 'object' && 'uri' in source && (!source.uri || source.uri === '');

  if (error || isUriEmpty) {
    return (
      <View
        style={[
          styles.fallbackContainer,
          { borderRadius },
          containerStyle,
          style as ViewStyle,
        ]}
      >
        <Text style={styles.fallbackIcon}>{fallbackText}</Text>
        <Text style={styles.fallbackLabel}>Image Unavailable</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { borderRadius }, containerStyle]}>
      {/* Underlying Shimmer Skeleton while loading */}
      {!loaded && (
        <SkeletonBox
          width="100%"
          height="100%"
          borderRadius={borderRadius}
          style={StyleSheet.absoluteFill as ViewStyle}
        />
      )}

      {/* Fade-in Cached Image */}
      <Animated.Image
        source={source as any}
        resizeMode={resizeMode}
        onLoad={handleLoad}
        onError={handleError}
        style={[
          style,
          {
            borderRadius,
            opacity: opacityAnim,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    overflow: 'hidden',
    backgroundColor: Colors.skeletonBase,
    justifyContent: 'center',
    alignItems: 'center',
  },
  fallbackContainer: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 8,
  },
  fallbackIcon: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.textMuted,
    marginBottom: 4,
  },
  fallbackLabel: {
    fontSize: 10,
    color: Colors.textDim,
    fontFamily: 'monospace',
  },
});
