import React, { useRef, useState } from 'react';
import {
  Animated,
  Image,
  ImageResizeMode,
  ImageSourcePropType,
  ImageStyle,
  StyleProp,
  StyleSheet,
  Text,
  View,
  ViewStyle,
} from 'react-native';
import { ApiClient } from '../api/client';
import { SkeletonBox } from './Skeleton';
import { Colors, Radius } from './Theme';

interface LazyImageProps {
  source: ImageSourcePropType | { uri: string | null | undefined };
  style?: StyleProp<ImageStyle>;
  containerStyle?: StyleProp<ViewStyle>;
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

  let finalSource = source;
  if (typeof source === 'object' && source !== null && 'uri' in source) {
    const rawUri = (source as any).uri;
    const resolvedUri = ApiClient.resolveMediaUrl(rawUri);
    finalSource = { ...(source as any), uri: resolvedUri };
  }

  const isUriEmpty =
    typeof finalSource === 'object' &&
    finalSource !== null &&
    'uri' in finalSource &&
    (!(finalSource as any).uri || (finalSource as any).uri === '');

  if (error || isUriEmpty) {
    return (
      <View
        style={[
          styles.container,
          styles.fallbackContainer,
          { borderRadius },
          style as ViewStyle,
          containerStyle,
        ]}
      >
        <Text style={styles.fallbackIcon}>{fallbackText}</Text>
        <Text style={styles.fallbackLabel}>Image Unavailable</Text>
      </View>
    );
  }

  return (
    <View
      style={[
        styles.container,
        { borderRadius },
        style as ViewStyle,
        containerStyle,
      ]}
    >
      {/* Underlying Shimmer Skeleton while loading */}
      {!loaded && (
        <SkeletonBox
          width="100%"
          height="100%"
          borderRadius={borderRadius}
          style={StyleSheet.absoluteFill as ViewStyle}
        />
      )}

      {/* Primary Image with robust rendering */}
      <Image
        source={finalSource as any}
        resizeMode={resizeMode}
        onLoad={() => setLoaded(true)}
        onError={() => {
          setError(true);
          setLoaded(true);
        }}
        style={[
          StyleSheet.absoluteFill,
          {
            borderRadius,
            opacity: loaded ? 1 : 0.01,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    height: '100%',
    overflow: 'hidden',
    backgroundColor: Colors.skeletonBase,
    position: 'relative',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fallbackContainer: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
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
