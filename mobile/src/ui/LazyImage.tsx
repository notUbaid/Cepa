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
import { resolveMediaUrl, getOfficerToken } from '../config';
import { SkeletonBox } from './Skeleton';
import { Colors, Radius } from './Theme';

interface LazyImageProps {
  source: ImageSourcePropType | { uri: string | null | undefined; headers?: Record<string, string> };
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

  // Automatically normalize URIs using active API base URL and attach officer auth header if needed
  const resolvedSource = React.useMemo(() => {
    if (typeof source === 'object' && source !== null && 'uri' in source) {
      const rawUri = (source as { uri?: string | null }).uri;
      const normalizedUri = resolveMediaUrl(rawUri);
      if (!normalizedUri) {
        return { uri: undefined };
      }
      const existingHeaders = (source as any).headers || {};
      const officerToken = getOfficerToken();
      return {
        ...source,
        uri: normalizedUri,
        headers: {
          ...existingHeaders,
          ...(officerToken ? { 'X-Officer-Token': officerToken } : {}),
        },
      };
    }
    return source;
  }, [source]);

  const isUriEmpty =
    typeof resolvedSource === 'object' &&
    resolvedSource !== null &&
    'uri' in resolvedSource &&
    (!resolvedSource.uri || resolvedSource.uri === '');

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
        source={resolvedSource as any}
        resizeMode={resizeMode}
        onLoad={() => setLoaded(true)}
        onError={(e: any) => {
          const failedUri = (resolvedSource as any)?.uri;
          console.warn('[LazyImage] Failed to render image from URI:', failedUri, e?.nativeEvent?.error);
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
