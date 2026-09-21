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
        <Text style={styles.loadingText}>Calibrating optical sensor...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <FadeInView delay={50} distance={15} style={styles.permCard}>
          <Text style={styles.permIcon}>📷</Text>
          <Text style={styles.permTitle}>Camera Access Required</Text>
          <Text style={styles.permDesc}>
            Cepa requires high-resolution optical feed to segment touching onion bulbs
            and detect ChArUco calibration cards.
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
              📁 Choose Existing Photo / Sample Spread
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
                    {inspection.lot_id || 'Lot #Pending'}
                  </Text>
                </View>
                <View style={styles.hudLevelTag}>
                  <View style={styles.levelBubble} />
                  <Text style={styles.hudLevelText}>PARALLEL LEVEL: OK</Text>
                </View>
              </View>
              <Text style={styles.hudInstructions}>
                Position phone ~70cm overhead. Ensure ChArUco card is visible in corner.
              </Text>
            </View>
          </FadeInView>

          {/* Center Target Frame */}
          <View style={styles.targetViewport}>
            {/* ChArUco Board Placement Bracket */}
            <View style={styles.charucoReticle}>
              <View style={[styles.cornerMini, styles.tlMini]} />
              <View style={[styles.cornerMini, styles.trMini]} />
              <View style={[styles.cornerMini, styles.blMini]} />
              <View style={[styles.cornerMini, styles.brMini]} />
              <Text style={styles.charucoLabel}>[ CHARUCO CARD ]</Text>
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
                  SPREAD 15–30 BULBS IN SINGLE LAYER
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
                scaleTo={0.9}
                style={styles.shutterOuter}
                onPress={takePhoto}
                disabled={capturing}
              >
                <View style={styles.shutterInner}>
                  {capturing ? (
                    <ActivityIndicator color={Colors.accent} size="small" />
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
                <Text style={styles.galleryIcon}>🖼️</Text>
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
  permIcon: {
    fontSize: 44,
    marginBottom: Spacing.md,
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
    backgroundColor: Colors.accentDark,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.accent,
    width: '100%',
    alignItems: 'center',
  },
  permBtnText: {
    color: Colors.text,
    fontWeight: '700',
    fontSize: 14,
  },
  galleryFallbackBtn: {
    marginTop: Spacing.md,
    padding: Spacing.sm,
  },
  galleryFallbackText: {
    color: Colors.accent,
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
    backgroundColor: 'rgba(7, 13, 24, 0.85)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  hudTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  hudLotTag: {
    backgroundColor: Colors.accentSubtle,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  hudLotText: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.accent,
    fontFamily: 'monospace',
  },
  hudLevelTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
  },
  levelBubble: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.gradeA,
  },
  hudLevelText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.gradeA,
  },
  hudInstructions: {
    fontSize: 11,
    color: Colors.textSecondary,
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
    width: 120,
    height: 80,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    borderWidth: 1,
    borderColor: Colors.accent,
    borderStyle: 'dashed',
    borderRadius: Radius.sm,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  charucoLabel: {
    fontSize: 9,
    fontWeight: '800',
    color: Colors.accent,
    fontFamily: 'monospace',
    letterSpacing: 0.5,
  },
  cornerMini: {
    position: 'absolute',
    width: 10,
    height: 10,
    borderColor: Colors.accent,
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
    borderColor: Colors.accent,
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
    backgroundColor: 'rgba(56, 189, 248, 0.4)',
  },
  crosshairV: {
    position: 'absolute',
    height: 18,
    width: 1.5,
    backgroundColor: 'rgba(56, 189, 248, 0.4)',
  },
  frameLabelBadge: {
    backgroundColor: 'rgba(7, 13, 24, 0.75)',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: Radius.pill,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
  },
  frameLabelText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.5,
  },
  controlsBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(7, 13, 24, 0.9)',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.pill,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cancelBtn: {
    padding: Spacing.sm,
  },
  cancelText: {
    color: Colors.textMuted,
    fontSize: 13,
    fontWeight: '700',
  },
  shutterOuter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(56, 189, 248, 0.25)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: Colors.accent,
  },
  shutterInner: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: Colors.cardBg,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: Colors.text,
  },
  shutterCore: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: Colors.accent,
  },
  galleryBtn: {
    alignItems: 'center',
    padding: Spacing.xs,
  },
  galleryIcon: {
    fontSize: 20,
  },
  galleryText: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '600',
    marginTop: 2,
  },
});
