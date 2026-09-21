import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { ApiClient } from '../api/client';
import { InspectionDetail, SampleDetail } from '../types';

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
  const [stage, setStage] = useState<'uploading' | 'analyzing' | 'done' | 'failed'>(
    'uploading'
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failureCodes, setFailureCodes] = useState<string[]>([]);
  const [sampleResult, setSampleResult] = useState<SampleDetail | null>(null);

  useEffect(() => {
    let isMounted = true;

    const processPhoto = async () => {
      try {
        setStage('uploading');
        const sample = await ApiClient.uploadSample(inspection.id, photoUri, {
          lat: inspection.geo_lat ?? undefined,
          lon: inspection.geo_lon ?? undefined,
          accuracy: inspection.location_accuracy ?? undefined,
        });

        if (!isMounted) return;

        if (sample.quality_passed && sample.processing_status === 'DONE') {
          setStage('done');
          setSampleResult(sample);
          setTimeout(() => {
            if (isMounted) onCheckPassed(sample);
          }, 1200);
        } else {
          setStage('failed');
          setFailureCodes(sample.quality_flags || []);
          setErrorMessage(
            sample.processing_error ||
              'Image quality validation failed. Please check the lighting, focus, or calibration board placement.'
          );
        }
      } catch (err: any) {
        if (!isMounted) return;
        setStage('failed');
        setErrorMessage(`Network or processing error: ${err.message}`);
      }
    };

    processPhoto();

    return () => {
      isMounted = false;
    };
  }, [inspection.id, photoUri]);

  return (
    <View style={styles.container}>
      {/* Photo Thumbnail */}
      <View style={styles.thumbnailContainer}>
        <Image source={{ uri: photoUri }} style={styles.thumbnail} resizeMode="cover" />
      </View>

      {/* Progress / Failure Card */}
      <View style={styles.card}>
        {stage === 'uploading' || stage === 'analyzing' ? (
          <View style={styles.stateCenter}>
            <ActivityIndicator size="large" color="#38bdf8" />
            <Text style={styles.stateTitle}>Evaluating Sample Quality</Text>
            <Text style={styles.stateSubtitle}>
              Running Laplacian blur analysis, exposure check, ChArUco detection, and
              YOLO11 instance segmentation...
            </Text>
          </View>
        ) : stage === 'done' ? (
          <View style={styles.stateCenter}>
            <Text style={styles.successIcon}>✓</Text>
            <Text style={styles.successTitle}>Quality Verification Passed</Text>
            <Text style={styles.successSubtitle}>
              Detected {sampleResult?.onion_count ?? 0} onion bulbs. Scale calibration
              locked at{' '}
              {sampleResult?.scale_mm_per_px
                ? `${sampleResult.scale_mm_per_px.toFixed(3)} mm/px`
                : 'N/A'}
              .
            </Text>
          </View>
        ) : (
          <View style={styles.failureContainer}>
            <Text style={styles.failureIcon}>⚠️</Text>
            <Text style={styles.failureTitle}>Image Not Usable</Text>
            <Text style={styles.failureDesc}>{errorMessage}</Text>

            {failureCodes.length > 0 && (
              <View style={styles.flagsList}>
                {failureCodes.map((code, idx) => (
                  <Text key={idx} style={styles.flagItem}>
                    • {code.replace(/_/g, ' ').toUpperCase()}
                  </Text>
                ))}
              </View>
            )}

            <TouchableOpacity style={styles.retakeBtn} onPress={onRetake}>
              <Text style={styles.retakeBtnText}>📷 Retake Photograph</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1b2a',
    padding: 16,
    justifyContent: 'center',
  },
  thumbnailContainer: {
    width: '100%',
    height: 220,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#000',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#334155',
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  card: {
    backgroundColor: '#1b263b',
    borderRadius: 14,
    padding: 24,
    borderWidth: 1,
    borderColor: '#243347',
  },
  stateCenter: {
    alignItems: 'center',
  },
  stateTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#f8f9fa',
    marginTop: 14,
  },
  stateSubtitle: {
    fontSize: 12,
    color: '#94a3b8',
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
  },
  successIcon: {
    fontSize: 32,
    color: '#2ecc71',
    fontWeight: 'bold',
  },
  successTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#2ecc71',
    marginTop: 8,
  },
  successSubtitle: {
    fontSize: 12,
    color: '#cbd5e1',
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
  },
  failureContainer: {
    alignItems: 'center',
  },
  failureIcon: {
    fontSize: 32,
    marginBottom: 4,
  },
  failureTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#e74c3c',
  },
  failureDesc: {
    fontSize: 13,
    color: '#f87171',
    textAlign: 'center',
    marginTop: 8,
    lineHeight: 18,
  },
  flagsList: {
    marginVertical: 12,
    backgroundColor: 'rgba(231, 76, 60, 0.15)',
    padding: 10,
    borderRadius: 8,
    width: '100%',
  },
  flagItem: {
    fontSize: 11,
    fontWeight: '700',
    color: '#ff7675',
    marginVertical: 2,
  },
  retakeBtn: {
    backgroundColor: '#e74c3c',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginTop: 10,
    width: '100%',
    alignItems: 'center',
  },
  retakeBtnText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '800',
  },
});
