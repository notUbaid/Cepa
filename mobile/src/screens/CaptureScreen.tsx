import React, { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { InspectionDetail } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  Haptics,
  Radius,
  Spacing,
  Typography,
} from '../ui';

interface CaptureScreenProps {
  inspection: InspectionDetail;
  onPhotoCaptured: (photoUri: string) => void;
  onCancel: () => void;
}

export const CaptureScreen: React.FC<CaptureScreenProps> = ({
  inspection,
  onPhotoCaptured,
  onCancel,
}) => {
  const [permission, requestPermission] = useCameraPermissions();
  const [capturing, setCapturing] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  const takePhoto = async () => {
    if (!cameraRef.current || capturing) return;
    Haptics.heavy();
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.95,
        skipProcessing: false,
      });
      if (photo?.uri) {
        Haptics.snap();
        onPhotoCaptured(photo.uri);
      }
    } catch (err: any) {
      Haptics.error();
      alert(`Camera capture error: ${err.message}`);
    } finally {
      setCapturing(false);
    }
  };

  const pickFromGallery = async () => {
    Haptics.light();
    try {
      const res = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 0.95,
      });
      if (!res.canceled && res.assets && res.assets.length > 0) {
        Haptics.snap();
        onPhotoCaptured(res.assets[0].uri);
      }
    } catch (err: any) {
      Haptics.error();
      alert(`Image selection error: ${err.message}`);
    }
  };

  if (!permission) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={Colors.accent} />
        <Text style={styles.loadingText}>Initializing camera sensor...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <FadeInView delay={50} distance={15} style={styles.permCard}>
          <View style={styles.permBadge}>
            <Text style={styles.permBadgeText}>Camera Permission</Text>
          </View>
          <Text style={styles.permTitle}>Camera Access Required</Text>
          <Text style={styles.permDesc}>
            Cepa requires camera access to measure onion diameters accurately and verify lot quality against APMC standards.
          </Text>
          <AnimatedPressable
            haptic="medium"
            style={styles.permBtn}
            onPress={requestPermission}
          >
            <Text style={styles.permBtnText}>Enable Camera</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="light"
            style={styles.galleryFallbackBtn}
            onPress={pickFromGallery}
          >
            <Text style={styles.galleryFallbackText}>
              Choose from Photo Library
            </Text>
          </AnimatedPressable>
        </FadeInView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={StyleSheet.absoluteFill}>
        <View style={styles.overlayContainer}>
          {/* Top HUD Bar */}
          <FadeInView delay={50} distance={-10}>
            <View style={styles.hudCard}>
              <View style={styles.hudTopRow}>
                <View style={styles.hudLotTag}>
                  <Text style={styles.hudLotText}>
                    {inspection.lot_id || 'Active Lot'}
                  </Text>
                </View>
                <View style={styles.hudLevelTag}>
                  <View style={styles.levelBubble} />
                  <Text style={styles.hudLevelText}>Level Balanced</Text>
                </View>
              </View>
              <Text style={styles.hudInstructions}>
                Position phone ~70 cm overhead. Ensure calibration card is placed in corner.
              </Text>
            </View>
          </FadeInView>

          {/* Center Target Frame */}
          <View style={styles.targetViewport}>
            {/* Calibration Marker Placement Bracket */}
            <View style={styles.charucoReticle}>
              <View style={[styles.cornerMini, styles.tlMini]} />
              <View style={[styles.cornerMini, styles.trMini]} />
              <View style={[styles.cornerMini, styles.blMini]} />
              <View style={[styles.cornerMini, styles.brMini]} />
              <Text style={styles.charucoLabel}>CALIBRATION CARD</Text>
            </View>

            {/* Main Onion Spread Frame */}
            <View style={styles.spreadFrame}>
              <View style={[styles.corner, styles.topLeft]} />
              <View style={[styles.corner, styles.topRight]} />
              <View style={[styles.corner, styles.bottomLeft]} />
              <View style={[styles.corner, styles.bottomRight]} />

              <View style={styles.centerCrosshair}>
                <View style={styles.crosshairH} />
                <View style={styles.crosshairV} />
              </View>

              <View style={styles.frameLabelBadge}>
                <Text style={styles.frameLabelText}>
                  Spread 15–30 bulbs flat in single layer
                </Text>
              </View>
            </View>
          </View>

          {/* Bottom Shutter Controls Bar */}
          <FadeInView delay={100} distance={15}>
            <View style={styles.controlsBar}>
              <AnimatedPressable
                haptic="light"
                style={styles.cancelBtn}
                onPress={onCancel}
                disabled={capturing}
              >
                <Text style={styles.cancelText}>Cancel</Text>
              </AnimatedPressable>

              {/* Tactile Shutter Button */}
              <AnimatedPressable
                haptic="heavy"
                scaleTo={0.92}
                style={styles.shutterOuter}
                onPress={takePhoto}
                disabled={capturing}
              >
                <View style={styles.shutterInner}>
                  {capturing ? (
                    <ActivityIndicator color="#18181b" size="small" />
                  ) : (
                    <View style={styles.shutterCore} />
                  )}
                </View>
              </AnimatedPressable>

              {/* Gallery Fallback */}
              <AnimatedPressable
                haptic="light"
                style={styles.galleryBtn}
                onPress={pickFromGallery}
                disabled={capturing}
              >
                <Text style={styles.galleryText}>Upload</Text>
              </AnimatedPressable>
            </View>
          </FadeInView>
        </View>
      </CameraView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  centerContainer: {
    flex: 1,
    backgroundColor: Colors.bg,
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.xl,
  },
  loadingText: {
    color: Colors.textMuted,
    marginTop: Spacing.md,
    fontSize: 13,
  },
  permCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.xl,
    padding: Spacing.xl,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
    width: '100%',
    maxWidth: 360,
  },
  permBadge: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.xs,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 8,
  },
  permBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textSecondary,
  },
  permTitle: {
    ...Typography.title1,
    color: Colors.text,
    textAlign: 'center',
    marginBottom: Spacing.sm,
  },
  permDesc: {
    ...Typography.body,
    color: Colors.textMuted,
    textAlign: 'center',
    marginBottom: Spacing.xl,
  },
  permBtn: {
    backgroundColor: Colors.accent,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.accent,
    width: '100%',
    alignItems: 'center',
  },
  permBtnText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 14,
  },
  galleryFallbackBtn: {
    marginTop: Spacing.md,
    padding: Spacing.sm,
  },
  galleryFallbackText: {
    color: Colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  overlayContainer: {
    flex: 1,
    justifyContent: 'space-between',
    paddingTop: 45,
    paddingBottom: 25,
    paddingHorizontal: Spacing.lg,
  },
  hudCard: {
    backgroundColor: 'rgba(24, 24, 27, 0.88)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  hudTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  hudLotTag: {
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  hudLotText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#ffffff',
  },
  hudLevelTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 8,
    paddingVertical: 2.5,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.25)',
  },
  levelBubble: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#ffffff',
  },
  hudLevelText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#ffffff',
  },
  hudInstructions: {
    fontSize: 11,
    color: '#d4d4d8',
    marginTop: 4,
    lineHeight: 16,
  },
  targetViewport: {
    flex: 1,
    marginVertical: Spacing.md,
    justifyContent: 'center',
    position: 'relative',
  },
  charucoReticle: {
    position: 'absolute',
    top: 10,
    left: 10,
    width: 130,
    height: 80,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.6)',
    borderStyle: 'dashed',
    borderRadius: Radius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  charucoLabel: {
    fontSize: 9,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: 0.5,
  },
  cornerMini: {
    position: 'absolute',
    width: 10,
    height: 10,
    borderColor: '#ffffff',
  },
  tlMini: { top: -1, left: -1, borderTopWidth: 2, borderLeftWidth: 2 },
  trMini: { top: -1, right: -1, borderTopWidth: 2, borderRightWidth: 2 },
  blMini: { bottom: -1, left: -1, borderBottomWidth: 2, borderLeftWidth: 2 },
  brMini: { bottom: -1, right: -1, borderBottomWidth: 2, borderRightWidth: 2 },
  spreadFrame: {
    flex: 1,
    marginVertical: Spacing.xl,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 28,
    height: 28,
    borderColor: '#ffffff',
  },
  topLeft: { top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3 },
  topRight: { top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3 },
  bottomLeft: { bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3 },
  bottomRight: { bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3 },
  centerCrosshair: {
    position: 'absolute',
    width: 30,
    height: 30,
    justifyContent: 'center',
    alignItems: 'center',
  },
  crosshairH: {
    position: 'absolute',
    width: 18,
    height: 1.5,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  crosshairV: {
    position: 'absolute',
    height: 18,
    width: 1.5,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
  },
  frameLabelBadge: {
    backgroundColor: 'rgba(24, 24, 27, 0.82)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  frameLabelText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#ffffff',
    letterSpacing: 0.2,
  },
  controlsBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(24, 24, 27, 0.90)',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  cancelBtn: {
    padding: Spacing.sm,
  },
  cancelText: {
    color: '#a1a1aa',
    fontSize: 13,
    fontWeight: '600',
  },
  shutterOuter: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#ffffff',
  },
  shutterInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  shutterCore: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#18181b',
  },
  galleryBtn: {
    alignItems: 'center',
    padding: Spacing.sm,
  },
  galleryText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
});
