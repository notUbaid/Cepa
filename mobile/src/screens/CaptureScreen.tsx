import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Image,
  Modal,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { ApiClient } from '../api/client';
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
  const [guideVisible, setGuideVisible] = useState(false);
  const [activeMode, setActiveMode] = useState<'SINGLE' | 'BATCH' | 'CALIBRATE'>('SINGLE');
  const [torchOn, setTorchOn] = useState(false);
  const cameraRef = useRef<CameraView>(null);

  // Artificial Gyroscopic Horizon (Simulated / Reactive)
  const [pitch, setPitch] = useState(-0.4);
  const [roll, setRoll] = useState(0.2);
  const isLevel = Math.abs(pitch) < 1.5 && Math.abs(roll) < 1.5;

  // Pulse animation for locked level
  const pulseAnim = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (isLevel) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.15, duration: 600, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulseAnim.setValue(1);
    }
  }, [isLevel]);

  // Gentle gyro simulation on web / tilt variation
  useEffect(() => {
    const interval = setInterval(() => {
      setPitch((prev) => {
        const delta = (Math.random() - 0.48) * 0.4;
        const next = Math.max(-2.5, Math.min(2.5, prev + delta));
        return parseFloat(next.toFixed(1));
      });
      setRoll((prev) => {
        const delta = (Math.random() - 0.5) * 0.4;
        const next = Math.max(-2.5, Math.min(2.5, prev + delta));
        return parseFloat(next.toFixed(1));
      });
    }, 1500);
    return () => clearInterval(interval);
  }, []);

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

  const loadDemoSample = () => {
    Haptics.medium();
    const demoUrl = ApiClient.getDemoSampleUrl();
    onPhotoCaptured(demoUrl);
  };

  if (!permission) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#ffffff" />
        <Text style={styles.loadingText}>Initializing optical grading sensor...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <FadeInView delay={50} distance={15} style={styles.permCard}>
          <View style={styles.permBadge}>
            <Text style={styles.permBadgeText}>OPTICAL SENSOR AUTHORIZATION</Text>
          </View>
          <Text style={styles.permTitle}>Camera Calibration Required</Text>
          <Text style={styles.permDesc}>
            Cepa requires top-down camera access to measure equatorial diameters and run AI defect classification against NAFED &amp; BIS standards.
          </Text>
          <AnimatedPressable
            haptic="medium"
            style={styles.permBtn}
            onPress={requestPermission}
          >
            <Text style={styles.permBtnText}>Enable Optical Sensor</Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="light"
            style={styles.galleryFallbackBtn}
            onPress={pickFromGallery}
          >
            <Text style={styles.galleryFallbackText}>
              Select Spread from Photo Library
            </Text>
          </AnimatedPressable>

          <AnimatedPressable
            haptic="medium"
            style={styles.demoCardBtn}
            onPress={loadDemoSample}
          >
            <Text style={styles.demoCardBtnText}>
              Load Mandi Demo Lot (32 Bulbs + ChArUco)
            </Text>
          </AnimatedPressable>
        </FadeInView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        enableTorch={torchOn}
      >
        <View style={styles.overlayContainer}>
          {/* Top Floating Aerospace HUD */}
          <FadeInView delay={50} distance={-10}>
            <View style={styles.topHudBar}>
              <AnimatedPressable
                haptic="light"
                onPress={onCancel}
                style={styles.hudCircleBtn}
              >
                <Text style={styles.hudCircleBtnText}>✕</Text>
              </AnimatedPressable>

              <View style={styles.hudCenterBadge}>
                <View style={styles.hudDotLive} />
                <View>
                  <Text style={styles.hudLotId}>
                    {inspection.lot_id ? `LOT: ${inspection.lot_id}` : 'CEPA OPTICAL SCANNER'}
                  </Text>
                  <Text style={styles.hudCentreText}>
                    {inspection.procurement_centre || 'Mandi Caliper Node'}
                  </Text>
                </View>
              </View>

              <View style={styles.hudRightActions}>
                {/* Guide Button */}
                <AnimatedPressable
                  haptic="selection"
                  onPress={() => setGuideVisible(true)}
                  style={styles.hudCircleBtn}
                >
                  <Text style={styles.hudGuideText}>?</Text>
                </AnimatedPressable>

                {/* Torch Toggle */}
                <AnimatedPressable
                  haptic="selection"
                  onPress={() => setTorchOn(!torchOn)}
                  style={[styles.hudCircleBtn, torchOn && styles.hudTorchActive]}
                >
                  <Text style={[styles.hudTorchText, torchOn && { color: '#000' }]}>
                    ⚡
                  </Text>
                </AnimatedPressable>
              </View>
            </View>
          </FadeInView>

          {/* Level Guidance & Altitude Bar */}
          <View style={styles.levelBannerWrap}>
            <View style={[styles.levelBanner, isLevel ? styles.levelBannerLocked : styles.levelBannerWarning]}>
              <Animated.View style={[styles.levelDot, isLevel && { transform: [{ scale: pulseAnim }] }]} />
              <Text style={styles.levelBannerText}>
                {isLevel
                  ? `HORIZON LOCKED · PITCH ${pitch > 0 ? '+' : ''}${pitch}° · ROLL ${roll > 0 ? '+' : ''}${roll}°`
                  : `ADJUST OVERHEAD TILT · PITCH ${pitch > 0 ? '+' : ''}${pitch}° · ROLL ${roll > 0 ? '+' : ''}${roll}°`}
              </Text>
            </View>
          </View>

          {/* Center Target Viewport with Aerospace Reticles */}
          <View style={styles.targetViewport}>
            {/* ChArUco Calibration Card Dock */}
            <View style={styles.charucoReticle}>
              <View style={[styles.cornerMini, styles.tlMini]} />
              <View style={[styles.cornerMini, styles.trMini]} />
              <View style={[styles.cornerMini, styles.blMini]} />
              <View style={[styles.cornerMini, styles.brMini]} />
              <View style={styles.charucoInnerPattern}>
                <View style={styles.checkerBox} />
                <View style={[styles.checkerBox, { backgroundColor: 'transparent' }]} />
                <View style={[styles.checkerBox, { backgroundColor: 'transparent' }]} />
                <View style={styles.checkerBox} />
              </View>
              <Text style={styles.charucoLabel}>ChArUco 7×5 BOARD DOCK</Text>
              <Text style={styles.charucoSubLabel}>40mm Scale Reference</Text>
            </View>

            {/* Left Edge Altitude Gauge */}
            <View style={styles.altitudeGauge}>
              <Text style={styles.altitudeText}>70cm</Text>
              <View style={styles.altitudeBarWrap}>
                <View style={styles.altitudeBarOptimal} />
                <View style={styles.altitudeCurrentMarker} />
              </View>
              <Text style={styles.altitudeSub}>ELEVATION</Text>
            </View>

            {/* Main Onion Spread Frame with Precision Corner Calipers */}
            <View style={styles.spreadFrame}>
              {/* Top-Left Corner Caliper */}
              <View style={[styles.caliperCorner, styles.cTopLeft]}>
                <View style={styles.tickH} />
                <View style={styles.tickV} />
              </View>
              {/* Top-Right Corner Caliper */}
              <View style={[styles.caliperCorner, styles.cTopRight]}>
                <View style={styles.tickH} />
                <View style={styles.tickV} />
              </View>
              {/* Bottom-Left Corner Caliper */}
              <View style={[styles.caliperCorner, styles.cBottomLeft]}>
                <View style={styles.tickH} />
                <View style={styles.tickV} />
              </View>
              {/* Bottom-Right Corner Caliper */}
              <View style={[styles.caliperCorner, styles.cBottomRight]}>
                <View style={styles.tickH} />
                <View style={styles.tickV} />
              </View>

              {/* Optical Center Crosshair with Concentric Aiming Rings */}
              <View style={styles.centerReticle}>
                <View style={styles.reticleRingOuter} />
                <View style={styles.reticleRingInner} />
                <View style={styles.reticleCrossH} />
                <View style={styles.reticleCrossV} />
                {isLevel && <View style={styles.reticleLockCenter} />}
              </View>

              {/* Dynamic Guidance Pill */}
              <View style={styles.guidancePill}>
                <Text style={styles.guidancePillText}>
                  Spread 15–30 bulbs in single layer · Avoid bulb overlap
                </Text>
              </View>
            </View>
          </View>

          {/* Bottom Industrial Shutter Deck */}
          <FadeInView delay={100} distance={15}>
            <View style={styles.bottomDeck}>
              {/* Mode Selector Tabs */}
              <View style={styles.modeTabsRow}>
                {(['SINGLE', 'BATCH', 'CALIBRATE'] as const).map((mode) => {
                  const active = activeMode === mode;
                  const labelMap = {
                    SINGLE: 'Single Lot',
                    BATCH: 'Rapid Batch',
                    CALIBRATE: 'Check Card',
                  };
                  return (
                    <AnimatedPressable
                      key={mode}
                      haptic="selection"
                      onPress={() => setActiveMode(mode)}
                      style={[styles.modeTab, active && styles.modeTabActive]}
                    >
                      <Text style={[styles.modeTabText, active && styles.modeTabTextActive]}>
                        {labelMap[mode]}
                      </Text>
                    </AnimatedPressable>
                  );
                })}
              </View>

              {/* Primary Control Deck */}
              <View style={styles.controlsRow}>
                {/* Photo Library Upload */}
                <AnimatedPressable
                  haptic="light"
                  style={styles.deckSideBtn}
                  onPress={pickFromGallery}
                  disabled={capturing}
                >
                  <View style={styles.sideBtnIconBox}>
                    <Text style={styles.sideBtnIcon}>🖼</Text>
                  </View>
                  <Text style={styles.sideBtnLabel}>Library</Text>
                </AnimatedPressable>

                {/* Tactile Shutter Button with Rotating Reticle */}
                <AnimatedPressable
                  haptic="heavy"
                  scaleTo={0.90}
                  style={[
                    styles.shutterOuterRing,
                    isLevel && styles.shutterOuterRingLevel,
                  ]}
                  onPress={takePhoto}
                  disabled={capturing}
                >
                  <View style={[styles.shutterMiddleHalo, isLevel && styles.shutterMiddleHaloLevel]}>
                    <View style={styles.shutterCoreButton}>
                      {capturing ? (
                        <ActivityIndicator color="#0c0c0e" size="small" />
                      ) : (
                        <View style={[styles.shutterCenterPip, isLevel && styles.shutterCenterPipLevel]} />
                      )}
                    </View>
                  </View>
                </AnimatedPressable>

                {/* Instant Mandi Demo Sample */}
                <AnimatedPressable
                  haptic="medium"
                  style={styles.deckSideBtn}
                  onPress={loadDemoSample}
                  disabled={capturing}
                >
                  <View style={[styles.sideBtnIconBox, styles.demoIconBox]}>
                    <Text style={styles.demoBadge}>DEMO</Text>
                  </View>
                  <Text style={styles.sideBtnLabel}>Test Lot</Text>
                </AnimatedPressable>
              </View>
            </View>
          </FadeInView>
        </View>
      </CameraView>

      {/* Interactive Calibration Station Guide Sheet Modal */}
      <Modal
        visible={guideVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setGuideVisible(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.guideCard}>
            <View style={styles.guideHeader}>
              <View>
                <Text style={styles.guideTitle}>Optical Calibration Guide</Text>
                <Text style={styles.guideSubtitle}>BIS IS 17912:2022 Optical Caliper Protocol</Text>
              </View>
              <AnimatedPressable
                haptic="light"
                onPress={() => setGuideVisible(false)}
                style={styles.guideCloseBtn}
              >
                <Text style={styles.guideCloseText}>✕</Text>
              </AnimatedPressable>
            </View>

            {/* 3D Isometric Station Graphic */}
            <View style={styles.guideImageWrap}>
              <Image
                source={require('../../assets/calibration_guide.png')}
                style={styles.guideImage}
                resizeMode="cover"
              />
            </View>

            {/* Guidance Steps */}
            <View style={styles.guideSteps}>
              <View style={styles.stepRow}>
                <View style={styles.stepNum}><Text style={styles.stepNumText}>1</Text></View>
                <View style={styles.stepInfo}>
                  <Text style={styles.stepTitle}>ChArUco 7×5 Calibration Board</Text>
                  <Text style={styles.stepDesc}>Place the 40mm reference card inside the top-left bracket.</Text>
                </View>
              </View>

              <View style={styles.stepRow}>
                <View style={styles.stepNum}><Text style={styles.stepNumText}>2</Text></View>
                <View style={styles.stepInfo}>
                  <Text style={styles.stepTitle}>Elevation &amp; Horizon</Text>
                  <Text style={styles.stepDesc}>Hold device ~70 cm directly overhead until horizon reticle turns emerald.</Text>
                </View>
              </View>

              <View style={styles.stepRow}>
                <View style={styles.stepNum}><Text style={styles.stepNumText}>3</Text></View>
                <View style={styles.stepInfo}>
                  <Text style={styles.stepTitle}>Single Layer Spread</Text>
                  <Text style={styles.stepDesc}>Spread 15–30 bulbs flat without touching or double-stacking.</Text>
                </View>
              </View>
            </View>

            <AnimatedPressable
              haptic="medium"
              onPress={() => setGuideVisible(false)}
              style={styles.guideActionBtn}
            >
              <Text style={styles.guideActionBtnText}>Understood · Return to Scanner</Text>
            </AnimatedPressable>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#0c0c0e',
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.xl,
  },
  loadingText: {
    color: '#a1a1aa',
    marginTop: Spacing.md,
    fontSize: 13,
    fontWeight: '500',
  },
  permCard: {
    backgroundColor: '#16161a',
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    width: '100%',
    maxWidth: 380,
  },
  permBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: Radius.xs,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    marginBottom: 10,
  },
  permBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#d4d4d8',
    letterSpacing: 0.5,
  },
  permTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: Spacing.sm,
  },
  permDesc: {
    fontSize: 13,
    color: '#a1a1aa',
    textAlign: 'center',
    marginBottom: Spacing.xl,
    lineHeight: 18,
  },
  permBtn: {
    backgroundColor: '#ffffff',
    paddingHorizontal: Spacing.xl,
    paddingVertical: 12,
    borderRadius: Radius.sm,
    width: '100%',
    alignItems: 'center',
  },
  permBtnText: {
    color: '#0c0c0e',
    fontWeight: '700',
    fontSize: 14,
  },
  galleryFallbackBtn: {
    marginTop: Spacing.md,
    padding: Spacing.sm,
  },
  galleryFallbackText: {
    color: '#a1a1aa',
    fontSize: 13,
    fontWeight: '600',
  },
  demoCardBtn: {
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    borderRadius: Radius.sm,
    paddingVertical: 12,
    paddingHorizontal: Spacing.lg,
    width: '100%',
    alignItems: 'center',
    marginTop: Spacing.sm,
  },
  demoCardBtnText: {
    color: '#ffffff',
    fontSize: 12,
    fontWeight: '600',
  },
  overlayContainer: {
    flex: 1,
    justifyContent: 'space-between',
    paddingTop: Platform.OS === 'ios' ? 52 : 36,
    paddingBottom: Platform.OS === 'ios' ? 34 : 20,
    paddingHorizontal: 16,
  },

  /* Top HUD Bar */
  topHudBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'rgba(12, 12, 14, 0.85)',
    borderRadius: 24,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
  },
  hudCircleBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  hudCircleBtnText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  hudGuideText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '800',
  },
  hudTorchText: {
    fontSize: 14,
  },
  hudTorchActive: {
    backgroundColor: '#f59e0b',
    borderColor: '#f59e0b',
  },
  hudCenterBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  hudDotLive: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10b981',
  },
  hudLotId: {
    fontSize: 12,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: 0.3,
  },
  hudCentreText: {
    fontSize: 10,
    color: '#a1a1aa',
    fontWeight: '500',
  },
  hudRightActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },

  /* Level Banner */
  levelBannerWrap: {
    alignItems: 'center',
    marginTop: 8,
  },
  levelBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 14,
    borderWidth: 1,
  },
  levelBannerLocked: {
    backgroundColor: 'rgba(16, 185, 129, 0.18)',
    borderColor: 'rgba(16, 185, 129, 0.4)',
  },
  levelBannerWarning: {
    backgroundColor: 'rgba(245, 158, 11, 0.18)',
    borderColor: 'rgba(245, 158, 11, 0.35)',
  },
  levelDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#ffffff',
  },
  levelBannerText: {
    fontSize: 10.5,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: 0.3,
  },

  /* Viewport Target */
  targetViewport: {
    flex: 1,
    marginVertical: 10,
    justifyContent: 'center',
    position: 'relative',
  },

  /* ChArUco Reticle Corner */
  charucoReticle: {
    position: 'absolute',
    top: 6,
    left: 6,
    width: 130,
    height: 90,
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
    borderWidth: 1.5,
    borderColor: '#38bdf8',
    borderStyle: 'dashed',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  charucoInnerPattern: {
    width: 24,
    height: 24,
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 4,
  },
  checkerBox: {
    width: 12,
    height: 12,
    backgroundColor: '#ffffff',
  },
  charucoLabel: {
    fontSize: 8.5,
    fontWeight: '800',
    color: '#38bdf8',
    letterSpacing: 0.4,
  },
  charucoSubLabel: {
    fontSize: 8,
    color: '#e0f2fe',
    marginTop: 1,
  },
  cornerMini: {
    position: 'absolute',
    width: 8,
    height: 8,
    borderColor: '#38bdf8',
  },
  tlMini: { top: -2, left: -2, borderTopWidth: 2, borderLeftWidth: 2 },
  trMini: { top: -2, right: -2, borderTopWidth: 2, borderRightWidth: 2 },
  blMini: { bottom: -2, left: -2, borderBottomWidth: 2, borderLeftWidth: 2 },
  brMini: { bottom: -2, right: -2, borderBottomWidth: 2, borderRightWidth: 2 },

  /* Altitude Gauge */
  altitudeGauge: {
    position: 'absolute',
    left: 6,
    top: 110,
    alignItems: 'center',
    backgroundColor: 'rgba(12, 12, 14, 0.75)',
    paddingVertical: 8,
    paddingHorizontal: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  altitudeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#10b981',
  },
  altitudeBarWrap: {
    width: 4,
    height: 60,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    borderRadius: 2,
    marginVertical: 4,
    position: 'relative',
    overflow: 'hidden',
  },
  altitudeBarOptimal: {
    position: 'absolute',
    top: 20,
    bottom: 20,
    width: '100%',
    backgroundColor: 'rgba(16, 185, 129, 0.6)',
  },
  altitudeCurrentMarker: {
    position: 'absolute',
    top: 28,
    width: 6,
    height: 4,
    left: -1,
    backgroundColor: '#ffffff',
    borderRadius: 1,
  },
  altitudeSub: {
    fontSize: 7,
    fontWeight: '700',
    color: '#71717a',
    letterSpacing: 0.3,
  },

  /* Spread Frame */
  spreadFrame: {
    flex: 1,
    marginHorizontal: 12,
    marginVertical: 16,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  caliperCorner: {
    position: 'absolute',
    width: 32,
    height: 32,
    borderColor: 'rgba(255, 255, 255, 0.85)',
  },
  cTopLeft: { top: 0, left: 0, borderTopWidth: 2.5, borderLeftWidth: 2.5 },
  cTopRight: { top: 0, right: 0, borderTopWidth: 2.5, borderRightWidth: 2.5 },
  cBottomLeft: { bottom: 0, left: 0, borderBottomWidth: 2.5, borderLeftWidth: 2.5 },
  cBottomRight: { bottom: 0, right: 0, borderBottomWidth: 2.5, borderRightWidth: 2.5 },
  tickH: {
    position: 'absolute',
    top: -6,
    left: 12,
    width: 1,
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
  },
  tickV: {
    position: 'absolute',
    left: -6,
    top: 12,
    width: 4,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
  },

  /* Optical Center Reticle */
  centerReticle: {
    width: 64,
    height: 64,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  reticleRingOuter: {
    position: 'absolute',
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.25)',
  },
  reticleRingInner: {
    position: 'absolute',
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.45)',
  },
  reticleCrossH: {
    position: 'absolute',
    width: 24,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
  },
  reticleCrossV: {
    position: 'absolute',
    height: 24,
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.6)',
  },
  reticleLockCenter: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#10b981',
  },

  /* Guidance Pill */
  guidancePill: {
    position: 'absolute',
    bottom: 8,
    backgroundColor: 'rgba(12, 12, 14, 0.82)',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  guidancePillText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#f4f4f5',
    letterSpacing: 0.2,
  },

  /* Bottom Industrial Shutter Deck */
  bottomDeck: {
    backgroundColor: 'rgba(12, 12, 14, 0.92)',
    borderRadius: 24,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  modeTabsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 12,
  },
  modeTab: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  modeTabActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
  },
  modeTabText: {
    fontSize: 10.5,
    fontWeight: '600',
    color: '#71717a',
    letterSpacing: 0.4,
  },
  modeTabTextActive: {
    color: '#ffffff',
    fontWeight: '700',
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
  },
  deckSideBtn: {
    alignItems: 'center',
    width: 56,
  },
  sideBtnIconBox: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    marginBottom: 4,
  },
  sideBtnIcon: {
    fontSize: 18,
  },
  demoIconBox: {
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    borderColor: 'rgba(245, 158, 11, 0.3)',
  },
  demoBadge: {
    fontSize: 9.5,
    fontWeight: '800',
    color: '#f59e0b',
    letterSpacing: 0.5,
  },
  sideBtnLabel: {
    fontSize: 10.5,
    fontWeight: '600',
    color: '#a1a1aa',
  },

  /* Shutter Ring */
  shutterOuterRing: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  shutterOuterRingLevel: {
    borderColor: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
  },
  shutterMiddleHalo: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  shutterMiddleHaloLevel: {
    backgroundColor: '#10b981',
  },
  shutterCoreButton: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
  },
  shutterCenterPip: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#0c0c0e',
  },
  shutterCenterPipLevel: {
    backgroundColor: '#047857',
  },

  /* Calibration Guide Modal */
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    justifyContent: 'flex-end',
  },
  guideCard: {
    backgroundColor: '#16161a',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: Spacing.xl,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    maxHeight: '90%',
  },
  guideHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: Spacing.md,
  },
  guideTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: -0.3,
  },
  guideSubtitle: {
    fontSize: 12,
    color: '#a1a1aa',
    marginTop: 2,
  },
  guideCloseBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  guideCloseText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '700',
  },
  guideImageWrap: {
    width: '100%',
    height: 190,
    borderRadius: Radius.md,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    marginBottom: Spacing.lg,
  },
  guideImage: {
    width: '100%',
    height: '100%',
  },
  guideSteps: {
    gap: 12,
    marginBottom: Spacing.xl,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  stepNum: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 1,
  },
  stepNumText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#ffffff',
  },
  stepInfo: {
    flex: 1,
  },
  stepTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#ffffff',
  },
  stepDesc: {
    fontSize: 11.5,
    color: '#a1a1aa',
    marginTop: 2,
    lineHeight: 16,
  },
  guideActionBtn: {
    backgroundColor: '#ffffff',
    paddingVertical: 14,
    borderRadius: Radius.md,
    alignItems: 'center',
  },
  guideActionBtnText: {
    color: '#0c0c0e',
    fontSize: 13.5,
    fontWeight: '700',
  },
});
