import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
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

  // Staggered checklist items for visual feedback
  const [checkProgress, setCheckProgress] = useState({
    blur: false,
    exposure: false,
    scale: false,
    segmentation: false,
  });

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
        }, 1400);
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
      {/* Captured Image Preview */}
      <FadeInView delay={50} distance={10}>
        <View style={styles.thumbnailContainer}>
          <LazyImage
            source={{ uri: currentPhotoUri }}
            style={styles.thumbnail}
            borderRadius={Radius.lg}
            resizeMode="cover"
          />
          <View style={styles.thumbnailBadge}>
            <Text style={styles.thumbnailBadgeText}>Captured Spread</Text>
          </View>
        </View>
      </FadeInView>

      {/* Progress / Results Card */}
      <FadeInView delay={120} distance={15}>
        <View style={styles.card}>
          {stage === 'uploading' || stage === 'analyzing' ? (
            <View style={styles.stateCenter}>
              <ActivityIndicator size="large" color={Colors.accent} />
              <Text style={styles.stateTitle}>Quality Verification</Text>
              <Text style={styles.stateSubtitle}>
                Checking image clarity, lighting uniformity, reference marker, and onion bulb separation...
              </Text>

              {/* Animated Checklist */}
              <View style={styles.checklist}>
                <CheckItem
                  label="1. Sharpness & Clarity"
                  passed={checkProgress.blur}
                />
                <CheckItem
                  label="2. Lighting & Glare Check"
                  passed={checkProgress.exposure}
                />
                <CheckItem
                  label="3. Reference Scale Marker"
                  passed={checkProgress.scale}
                />
                <CheckItem
                  label="4. Onion Separation & Defect Scan"
                  passed={checkProgress.segmentation}
                />
              </View>
            </View>
          ) : stage === 'done' ? (
            <View style={styles.stateCenter}>
              <View style={styles.successBadge}>
                <Text style={styles.successIcon}>✓</Text>
              </View>
              <Text style={styles.successTitle}>Quality Verification Passed</Text>
              <Text style={styles.successSubtitle}>
                Identified {sampleResult?.onion_count ?? 0} onion bulbs.{' '}
                {sampleResult?.scale_mm_per_px && (
                  <Text style={styles.scaleLockText}>
                    Scale calibrated at {sampleResult.scale_mm_per_px.toFixed(3)} mm/px.
                  </Text>
                )}
              </Text>
              <Text style={styles.redirectText}>Opening assessment results...</Text>
            </View>
          ) : (
            <View style={styles.failureContainer}>
              <View style={styles.failBadge}>
                <Text style={styles.failIcon}>✕</Text>
              </View>
              <Text style={styles.failureTitle}>Verification Incomplete</Text>
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

const CheckItem: React.FC<{ label: string; passed: boolean }> = ({ label, passed }) => (
  <View style={styles.checkItemRow}>
    <View
      style={[
        styles.checkDot,
        {
          backgroundColor: passed ? Colors.accent : Colors.cardBgElevated,
          borderColor: passed ? Colors.accent : Colors.borderMuted,
        },
      ]}
    >
      {passed && <Text style={styles.checkTick}>✓</Text>}
    </View>
    <Text
      style={[
        styles.checkItemLabel,
        { color: passed ? Colors.text : Colors.textMuted },
      ]}
    >
      {label}
    </Text>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    justifyContent: 'center',
  },
  thumbnailContainer: {
    width: '100%',
    height: 200,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    marginBottom: Spacing.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    position: 'relative',
    ...Shadows.card,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  thumbnailBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: Colors.cardBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: Radius.xs,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  thumbnailBadgeText: {
    fontSize: 10,
    fontWeight: '600',
    color: Colors.textSecondary,
  },
  card: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.xl,
    padding: Spacing.xl,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.card,
  },
  stateCenter: {
    alignItems: 'center',
  },
  stateTitle: {
    ...Typography.title2,
    color: Colors.text,
    marginTop: Spacing.md,
  },
  stateSubtitle: {
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: Spacing.xs,
    lineHeight: 18,
  },
  checklist: {
    width: '100%',
    marginTop: Spacing.lg,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
    gap: 10,
  },
  checkItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  checkDot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkTick: {
    fontSize: 10,
    fontWeight: '800',
    color: '#ffffff',
  },
  checkItemLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
  successBadge: {
    width: 44,
    height: 44,
    borderRadius: Radius.sm,
    backgroundColor: Colors.accent,
    justifyContent: 'center',
    alignItems: 'center',
  },
  successIcon: {
    fontSize: 20,
    color: '#ffffff',
    fontWeight: '700',
  },
  successTitle: {
    ...Typography.title1,
    color: Colors.text,
    marginTop: Spacing.md,
  },
  successSubtitle: {
    fontSize: 13,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
  },
  scaleLockText: {
    color: Colors.text,
    fontWeight: '600',
  },
  redirectText: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: Spacing.lg,
    fontWeight: '500',
  },
  failureContainer: {
    alignItems: 'center',
  },
  failBadge: {
    width: 44,
    height: 44,
    borderRadius: Radius.sm,
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  failIcon: {
    fontSize: 16,
    color: Colors.textSecondary,
    fontWeight: '700',
  },
  failureTitle: {
    ...Typography.title2,
    color: Colors.text,
    marginTop: Spacing.md,
  },
  failureDesc: {
    fontSize: 13,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: Spacing.xs,
    lineHeight: 19,
    paddingHorizontal: Spacing.sm,
  },
  flagsList: {
    marginVertical: Spacing.md,
    backgroundColor: Colors.cardBgElevated,
    padding: Spacing.md,
    borderRadius: Radius.sm,
    width: '100%',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  flagItem: {
    fontSize: 11,
    fontWeight: '500',
    color: Colors.textSecondary,
    marginVertical: 2,
  },
  actionBtnGroup: {
    width: '100%',
    gap: 8,
    marginTop: Spacing.md,
  },
  retakeBtn: {
    backgroundColor: Colors.accent,
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
    fontWeight: '600',
  },
  demoRetryBtn: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingVertical: 11,
    paddingHorizontal: Spacing.lg,
    borderRadius: Radius.sm,
    width: '100%',
    alignItems: 'center',
  },
  demoRetryBtnText: {
    color: Colors.text,
    fontSize: 12,
    fontWeight: '600',
  },
});
