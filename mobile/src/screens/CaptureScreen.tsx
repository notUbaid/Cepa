import React, { useRef, useState } from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { InspectionDetail } from '../types';

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
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.95,
        skipProcessing: false,
      });
      if (photo?.uri) {
        onPhotoCaptured(photo.uri);
      }
    } catch (err: any) {
      alert(`Camera capture error: ${err.message}`);
    } finally {
      setCapturing(false);
    }
  };

  const pickFromGallery = async () => {
    try {
      const res = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 0.95,
      });
      if (!res.canceled && res.assets && res.assets.length > 0) {
        onPhotoCaptured(res.assets[0].uri);
      }
    } catch (err: any) {
      alert(`Image pick error: ${err.message}`);
    }
  };

  if (!permission) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#38bdf8" />
        <Text style={styles.loadingText}>Initializing camera...</Text>
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.permTitle}>Camera Permission Required</Text>
        <Text style={styles.permDesc}>
          Cepa requires camera access to photograph and inspect the onion spread.
        </Text>
        <TouchableOpacity style={styles.permBtn} onPress={requestPermission}>
          <Text style={styles.permBtnText}>Grant Camera Permission</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.galleryFallbackBtn} onPress={pickFromGallery}>
          <Text style={styles.galleryFallbackText}>
            📁 Choose Existing Photo / Demo Sample
          </Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <CameraView ref={cameraRef} style={StyleSheet.absoluteFill}>
        {/* Safe Framing Guides */}
        <View style={styles.overlayContainer}>
          {/* Top Instructions Header */}
          <View style={styles.guidanceHeader}>
            <Text style={styles.guidanceTitle}>
              SAMPLE CAPTURE GUIDE • {inspection.lot_id || 'Lot'}
            </Text>
            <Text style={styles.guidanceInstructions}>
              1. Keep camera ~60–80 cm directly above the spread (parallel).{'\n'}
              2. Ensure the ChArUco calibration card is inside the top marker zone.
            </Text>
          </View>

          {/* Marker Reticle Target Area (Top Left) */}
          <View style={styles.markerReticle}>
            <Text style={styles.markerReticleLabel}>
              [ PLACE CHARUCO BOARD HERE ]
            </Text>
          </View>

          {/* Main Spread Center Reticle */}
          <View style={styles.spreadTarget}>
            <View style={[styles.corner, styles.topLeft]} />
            <View style={[styles.corner, styles.topRight]} />
            <View style={[styles.corner, styles.bottomLeft]} />
            <View style={[styles.corner, styles.bottomRight]} />
            <Text style={styles.spreadTargetLabel}>
              SPREAD ONIONS IN A SINGLE LAYER INSIDE FRAME
            </Text>
          </View>

          {/* Bottom Controls Bar */}
          <View style={styles.controlsBar}>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={onCancel}
              disabled={capturing}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>

            {/* Shutter Trigger */}
            <TouchableOpacity
              style={styles.shutterButton}
              onPress={takePhoto}
              disabled={capturing}
            >
              <View style={styles.shutterInner}>
                {capturing && <ActivityIndicator color="#0284c7" size="small" />}
              </View>
            </TouchableOpacity>

            {/* Gallery Upload Fallback */}
            <TouchableOpacity
              style={styles.galleryButton}
              onPress={pickFromGallery}
              disabled={capturing}
            >
              <Text style={styles.galleryIcon}>🖼️</Text>
              <Text style={styles.galleryText}>Upload</Text>
            </TouchableOpacity>
          </View>
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
    backgroundColor: '#0d1b2a',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    color: '#94a3b8',
    marginTop: 12,
    fontSize: 13,
  },
  permTitle: {
    color: '#f8f9fa',
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 8,
  },
  permDesc: {
    color: '#94a3b8',
    fontSize: 13,
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 18,
  },
  permBtn: {
    backgroundColor: '#0284c7',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  permBtnText: {
    color: '#fff',
    fontWeight: '700',
  },
  galleryFallbackBtn: {
    marginTop: 16,
    padding: 10,
  },
  galleryFallbackText: {
    color: '#38bdf8',
    fontSize: 13,
    fontWeight: '600',
  },
  overlayContainer: {
    flex: 1,
    justifyContent: 'space-between',
    paddingTop: 45,
    paddingBottom: 25,
    paddingHorizontal: 16,
  },
  guidanceHeader: {
    backgroundColor: 'rgba(13, 27, 42, 0.85)',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#38bdf8',
  },
  guidanceTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#38bdf8',
    letterSpacing: 0.5,
  },
  guidanceInstructions: {
    fontSize: 11,
    color: '#e2e8f0',
    marginTop: 4,
    lineHeight: 16,
  },
  markerReticle: {
    width: 140,
    height: 90,
    borderWidth: 2,
    borderColor: '#38bdf8',
    borderStyle: 'dashed',
    borderRadius: 6,
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 12,
  },
  markerReticleLabel: {
    color: '#38bdf8',
    fontSize: 8,
    fontWeight: '800',
    textAlign: 'center',
  },
  spreadTarget: {
    flex: 1,
    marginVertical: 12,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  spreadTargetLabel: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
    color: '#cbd5e1',
    fontSize: 10,
    fontWeight: '700',
  },
  corner: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderColor: '#38bdf8',
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: 3,
    borderRightWidth: 3,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 3,
    borderRightWidth: 3,
  },
  controlsBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(13, 27, 42, 0.85)',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 36,
  },
  cancelButton: {
    padding: 8,
  },
  cancelText: {
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '700',
  },
  shutterButton: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 4,
    borderColor: '#0284c7',
  },
  shutterInner: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#f8f9fa',
    justifyContent: 'center',
    alignItems: 'center',
  },
  galleryButton: {
    alignItems: 'center',
    padding: 6,
  },
  galleryIcon: {
    fontSize: 18,
  },
  galleryText: {
    color: '#94a3b8',
    fontSize: 10,
    fontWeight: '600',
  },
});
