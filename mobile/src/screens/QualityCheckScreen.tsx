import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Platform,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { InspectionDetail, SampleDetail } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  Haptics,
  LazyImage,
  Radius,
  Shadows,
  Spacing,
  Typography,
} from '../ui';

interface QualityCheckScreenProps {
  inspection: InspectionDetail;
  photoUri: string;
  onCheckPassed: (sample: SampleDetail) => void;
  onRetake: () => void;
}

export const QualityCheckScreen: React.FC<QualityCheckScreenProps> = ({
  inspection,
  photoUri,
  onCheckPassed,
  onRetake,
}) => {
  const [currentPhotoUri, setCurrentPhotoUri] = useState(photoUri);
  const [stage, setStage] = useState<'uploading' | 'analyzing' | 'done' | 'failed'>(
    'uploading'
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failureCodes, setFailureCodes] = useState<string[]>([]);
  const [sampleResult, setSampleResult] = useState<SampleDetail | null>(null);

  // Laser beam scanning animation
  const scanLineAnim = useRef(new Animated.Value(0)).current;

  // Staggered checklist items for visual feedback
  const [checkProgress, setCheckProgress] = useState({
    blur: false,
    exposure: false,
    scale: false,
    segmentation: false,
  });

  useEffect(() => {
    const scanLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(scanLineAnim, {
          toValue: 200,
          duration: 1400,
          useNativeDriver: true,
        }),
        Animated.timing(scanLineAnim, {
          toValue: 0,
          duration: 1400,
          useNativeDriver: true,
        }),
      ])
    );
    scanLoop.start();
    return () => scanLoop.stop();
  }, [scanLineAnim]);

  const processPhoto = async (targetUri: string) => {
    let isMounted = true;
    try {
      setStage('uploading');
      setErrorMessage(null);
      setFailureCodes([]);

      setTimeout(() => {
        if (isMounted) {
          setCheckProgress((p) => ({ ...p, blur: true }));
          Haptics.light();
        }
      }, 350);

      setTimeout(() => {
        if (isMounted) {
          setCheckProgress((p) => ({ ...p, exposure: true }));
          Haptics.light();
        }
      }, 700);

      const sample = await ApiClient.uploadSample(inspection.id, targetUri, {
        lat: inspection.geo_lat ?? undefined,
        lon: inspection.geo_lon ?? undefined,
        accuracy: inspection.location_accuracy ?? undefined,
      });

      if (!isMounted) return;

      if (sample.quality_passed && sample.processing_status === 'DONE') {
        setCheckProgress({
          blur: true,
          exposure: true,
          scale: true,
          segmentation: true,
        });
        setStage('done');
        setSampleResult(sample);
        Haptics.success();

        setTimeout(() => {
          if (isMounted) onCheckPassed(sample);
        }, 1200);
      } else {
        setStage('failed');
        setFailureCodes(sample.quality_flags || []);
        setErrorMessage(
          sample.processing_error ||
            'Spread arrangement or reference marker could not be verified. Ensure all bulbs are separated and the calibration card is visible.'
        );
        Haptics.error();
      }
    } catch (err: any) {
      if (!isMounted) return;
      setStage('failed');
      let cleanMsg = 'Verification could not be completed.';
      if (err.message) {
        const raw = String(err.message);
        if (raw.includes('Upload failed') || raw.includes('422') || raw.includes('Expected UploadFile')) {
          cleanMsg = 'Image file could not be read or uploaded. Please try capturing or selecting another photo.';
        } else if (raw.includes('Network') || raw.includes('Failed to fetch') || raw.includes('connect')) {
          cleanMsg = 'Cannot reach the Mandi verification service. Ensure the local server is running on port 8000.';
        } else {
          cleanMsg = raw.replace(/\{.*\}/g, '').trim() || cleanMsg;
        }
      }
      setErrorMessage(cleanMsg);
      Haptics.error();
    }
  };

  useEffect(() => {
    processPhoto(currentPhotoUri);
  }, []);

  const handleLoadDemo = () => {
    Haptics.medium();
    const demoUrl = ApiClient.getDemoSampleUrl();
    setCurrentPhotoUri(demoUrl);
    processPhoto(demoUrl);
  };

  return (
    <View style={styles.container}>
      {/* Captured Image Preview with Laser Scanning Overlay */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.thumbnailContainer}>
          <LazyImage
            source={{ uri: currentPhotoUri }}
            style={styles.thumbnail}
            borderRadius={Radius.lg}
            resizeMode="cover"
          />

          {/* Laser Scanning Line */}
          {(stage === 'uploading' || stage === 'analyzing') && (
            <Animated.View
              style={[
                styles.scanLine,
                { transform: [{ translateY: scanLineAnim }] },
              ]}
            >
              <View style={styles.scanLineBeam} />
            </Animated.View>
          )}

          {/* Scanning Telemetry HUD Overlay */}
          <View style={styles.thumbnailBadge}>
            <View style={styles.liveScanDot} />
            <Text style={styles.thumbnailBadgeText}>
              {stage === 'done' ? 'SCAN COMPLETE' : 'CV PIPELINE ACTIVE'}
            </Text>
          </View>

          <View style={styles.thumbnailBottomHud}>
            <Text style={styles.hudMetricText}>4K SENSOR · BIS IS 17912:2022</Text>
          </View>
        </View>
      </FadeInView>

      {/* Progress / Results Card */}
      <FadeInView delay={120} distance={15}>
        <View style={styles.card}>
          {stage === 'uploading' || stage === 'analyzing' ? (
            <View style={styles.stateCenter}>
              <ActivityIndicator size="large" color="#0c0c0e" />
              <Text style={styles.stateTitle}>Optical Quality Gate</Text>
              <Text style={styles.stateSubtitle}>
                Running multi-stage image verification: Laplacian blur variance, lux lighting check, ChArUco lock, and watershed segmentation...
              </Text>

              {/* Animated Checklist */}
              <View style={styles.checklist}>
                <CheckItem
                  label="1. Sharpness &amp; Blur Variance Check"
                  sub="Laplacian σ² > 100"
                  passed={checkProgress.blur}
                />
                <CheckItem
                  label="2. Lighting &amp; Glare Uniformity"
                  sub="Exposure 15–85% RGB dynamic range"
                  passed={checkProgress.exposure}
                />
                <CheckItem
                  label="3. Reference Scale Calibration"
                  sub="ChArUco 7×5 corner lock"
                  passed={checkProgress.scale}
                />
                <CheckItem
                  label="4. Separation &amp; AI Defect Analysis"
                  sub="MobileNetV3 + CIELAB mold detector"
                  passed={checkProgress.segmentation}
                />
              </View>
            </View>
          ) : stage === 'done' ? (
            <View style={styles.stateCenter}>
              <View style={styles.successBadge}>
                <Text style={styles.successIcon}>✓</Text>
              </View>
              <Text style={styles.successTitle}>Verification Certified</Text>
              <Text style={styles.successSubtitle}>
                Segmented <Text style={{ fontWeight: '800', color: '#0c0c0e' }}>{sampleResult?.onion_count ?? 0} onion bulbs</Text>.{' '}
                {sampleResult?.scale_mm_per_px && (
                  <Text style={styles.scaleLockText}>
                    Scale locked at {sampleResult.scale_mm_per_px.toFixed(4)} mm/px.
                  </Text>
                )}
              </Text>
              <Text style={styles.redirectText}>Opening commercial appraisal dossier...</Text>
            </View>
          ) : (
            <View style={styles.failureContainer}>
              <View style={styles.failBadge}>
                <Text style={styles.failIcon}>✕</Text>
              </View>
              <Text style={styles.failureTitle}>Quality Gate Verification Failed</Text>
              <Text style={styles.failureDesc}>{errorMessage}</Text>

              {failureCodes.length > 0 && (
                <View style={styles.flagsList}>
                  {failureCodes.map((code, idx) => (
                    <Text key={idx} style={styles.flagItem}>
                      • {code.replace(/_/g, ' ')}
                    </Text>
                  ))}
                </View>
              )}

              <View style={styles.actionBtnGroup}>
                <AnimatedPressable
                  haptic="medium"
                  style={styles.retakeBtn}
                  onPress={onRetake}
                >
                  <Text style={styles.retakeBtnText}>Retake Photograph</Text>
                </AnimatedPressable>

                <AnimatedPressable
                  haptic="light"
                  style={styles.demoRetryBtn}
                  onPress={handleLoadDemo}
                >
                  <Text style={styles.demoRetryBtnText}>Load Mandi Demo Lot Sample</Text>
                </AnimatedPressable>
              </View>
            </View>
          )}
        </View>
      </FadeInView>
    </View>
  );
};

const CheckItem: React.FC<{ label: string; sub?: string; passed: boolean }> = ({
  label,
  sub,
  passed,
}) => (
  <View style={styles.checkItemRow}>
    <View
      style={[
        styles.checkDot,
        {
          backgroundColor: passed ? '#10b981' : '#f4f3ef',
          borderColor: passed ? '#10b981' : '#e7e5e4',
        },
      ]}
    >
      {passed && <Text style={styles.checkTick}>✓</Text>}
    </View>
    <View style={{ flex: 1 }}>
      <Text
        style={[
          styles.checkItemLabel,
          { color: passed ? '#0c0c0e' : '#71717a', fontWeight: passed ? '700' : '500' },
        ]}
      >
        {label}
      </Text>
      {sub && <Text style={styles.checkItemSub}>{sub}</Text>}
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9f8f6',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    justifyContent: 'center',
  },
  thumbnailContainer: {
    width: '100%',
    height: 210,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: '#e7e5e4',
    position: 'relative',
    ...Shadows.card,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  scanLine: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 2,
    zIndex: 10,
  },
  scanLineBeam: {
    height: 2,
    backgroundColor: '#38bdf8',
    shadowColor: '#38bdf8',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 8,
  },
  thumbnailBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: 'rgba(12, 12, 14, 0.85)',
    paddingHorizontal: 8,
    paddingVertical: 3.5,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  liveScanDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#38bdf8',
  },
  thumbnailBadgeText: {
    fontSize: 9.5,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: 0.5,
  },
  thumbnailBottomHud: {
    position: 'absolute',
    bottom: 8,
    left: 10,
    backgroundColor: 'rgba(12, 12, 14, 0.75)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 3,
  },
  hudMetricText: {
    fontSize: 9,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    color: '#a1a1aa',
    letterSpacing: 0.4,
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    borderWidth: 1,
    borderColor: '#e7e5e4',
    ...Shadows.card,
  },
  stateCenter: {
    alignItems: 'center',
  },
  stateTitle: {
    ...Typography.title2,
    fontSize: 17,
    fontWeight: '800',
    color: '#0c0c0e',
    marginTop: Spacing.md,
  },
  stateSubtitle: {
    fontSize: 11.5,
    color: '#71717a',
    textAlign: 'center',
    marginTop: Spacing.xs,
    lineHeight: 17,
  },
  checklist: {
    width: '100%',
    marginTop: Spacing.lg,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: '#f5f5f4',
    gap: 12,
  },
  checkItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  checkDot: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkTick: {
    fontSize: 11,
    fontWeight: '800',
    color: '#ffffff',
  },
  checkItemLabel: {
    fontSize: 12.5,
  },
  checkItemSub: {
    fontSize: 10.5,
    color: '#a1a1aa',
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    marginTop: 1,
  },
  successBadge: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#10b981',
    justifyContent: 'center',
    alignItems: 'center',
  },
  successIcon: {
    fontSize: 24,
    color: '#ffffff',
    fontWeight: '800',
  },
  successTitle: {
    ...Typography.title1,
    fontSize: 18,
    fontWeight: '800',
    color: '#0c0c0e',
    marginTop: Spacing.md,
  },
  successSubtitle: {
    fontSize: 13,
    color: '#52525b',
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
  },
  scaleLockText: {
    color: '#047857',
    fontWeight: '700',
  },
  redirectText: {
    fontSize: 11.5,
    color: '#71717a',
    marginTop: Spacing.lg,
    fontWeight: '600',
  },
  failureContainer: {
    alignItems: 'center',
  },
  failBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#fef2f2',
    borderWidth: 1,
    borderColor: '#fecaca',
    justifyContent: 'center',
    alignItems: 'center',
  },
  failIcon: {
    fontSize: 16,
    color: '#ef4444',
    fontWeight: '800',
  },
  failureTitle: {
    ...Typography.title2,
    fontSize: 16,
    fontWeight: '800',
    color: '#991b1b',
    marginTop: Spacing.md,
  },
  failureDesc: {
    fontSize: 12.5,
    color: '#52525b',
    textAlign: 'center',
    marginTop: Spacing.xs,
    lineHeight: 18,
    paddingHorizontal: Spacing.sm,
  },
  flagsList: {
    marginVertical: Spacing.md,
    backgroundColor: '#fef2f2',
    padding: Spacing.md,
    borderRadius: Radius.sm,
    width: '100%',
    borderWidth: 1,
    borderColor: '#fecaca',
  },
  flagItem: {
    fontSize: 11,
    fontWeight: '600',
    color: '#991b1b',
    marginVertical: 2,
  },
  actionBtnGroup: {
    width: '100%',
    gap: 8,
    marginTop: Spacing.md,
  },
  retakeBtn: {
    backgroundColor: '#0c0c0e',
    paddingVertical: 12,
    paddingHorizontal: Spacing.lg,
    borderRadius: Radius.sm,
    width: '100%',
    alignItems: 'center',
    ...Shadows.card,
  },
  retakeBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
  },
  demoRetryBtn: {
    backgroundColor: '#f4f3ef',
    borderWidth: 1,
    borderColor: '#e7e5e4',
    paddingVertical: 11,
    paddingHorizontal: Spacing.lg,
    borderRadius: Radius.sm,
    width: '100%',
    alignItems: 'center',
  },
  demoRetryBtnText: {
    color: '#0c0c0e',
    fontSize: 12,
    fontWeight: '700',
  },
});
