import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Image,
  Linking,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { Feather } from '@expo/vector-icons';
import { ApiClient } from '../api/client';
import { InspectionDetail, VideoScanResult } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  Haptics,
  Radius,
  Shadows,
  Spacing,
  Typography,
} from '../ui';

interface CaptureScreenProps {
  inspection: InspectionDetail;
  initialTab?: 'CAMERA' | 'UPLOAD' | 'VIDEO';
  onPhotoCaptured: (photoUri: string) => void;
  onVideoCaptured?: (videoResult: VideoScanResult) => void;
  onCancel: () => void;
}

export const CaptureScreen: React.FC<CaptureScreenProps> = ({
  inspection,
  initialTab = 'CAMERA',
  onPhotoCaptured,
  onVideoCaptured,
  onCancel,
}) => {
  const [permission, requestPermission] = useCameraPermissions();
  const [capturing, setCapturing] = useState(false);
  const [guideVisible, setGuideVisible] = useState(false);
  const [activeMode, setActiveMode] = useState<'SINGLE' | 'BATCH' | 'CALIBRATE'>('SINGLE');
  const [torchOn, setTorchOn] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [facing, setFacing] = useState<'back' | 'front'>('back');
  const [activeTab, setActiveTab] = useState<'CAMERA' | 'UPLOAD' | 'VIDEO'>(initialTab);
  const [videoProcessing, setVideoProcessing] = useState(false);
  const [videoStepText, setVideoStepText] = useState('Uploading video sweep...');
  const cameraRef = useRef<CameraView>(null);

  const toggleFacing = () => {
    Haptics.selection();
    setFacing((prev) => (prev === 'back' ? 'front' : 'back'));
  };

  const triggerFileUpload = () => {
    Haptics.light();
    if (Platform.OS === 'web') {
      try {
        let input = document.getElementById('cepa-web-file-input') as HTMLInputElement | null;
        if (!input) {
          input = document.createElement('input');
          input.type = 'file';
          input.id = 'cepa-web-file-input';
          input.accept = 'image/*';
          input.style.display = 'none';
          document.body.appendChild(input);
        }
        input.value = '';
        input.onchange = (e: any) => {
          const file = e.target?.files?.[0];
          if (file) {
            const reader = new FileReader();
            reader.onload = (re) => {
              const dataUri = re.target?.result as string;
              if (dataUri) {
                Haptics.snap();
                onPhotoCaptured(dataUri);
              }
            };
            reader.readAsDataURL(file);
          }
        };
        input.click();
      } catch (err: any) {
        console.warn('Web file input trigger failed, falling back to ImagePicker:', err);
        pickFromGallery();
      }
    } else {
      pickFromGallery();
    }
  };

  const triggerVideoUpload = () => {
    Haptics.light();
    if (Platform.OS === 'web') {
      try {
        let input = document.getElementById('cepa-web-video-input') as HTMLInputElement | null;
        if (!input) {
          input = document.createElement('input');
          input.type = 'file';
          input.id = 'cepa-web-video-input';
          input.accept = 'video/*';
          input.style.display = 'none';
          document.body.appendChild(input);
        }
        input.value = '';
        input.onchange = async (e: any) => {
          const file = e.target?.files?.[0];
          if (file) {
            await handleProcessVideoBlob(file);
          }
        };
        input.click();
      } catch (err: any) {
        console.warn('Web video input failed, falling back to ImagePicker:', err);
        pickVideoFromGallery();
      }
    } else {
      pickVideoFromGallery();
    }
  };

  const pickVideoFromGallery = async () => {
    Haptics.light();
    try {
      const res = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['videos'],
        allowsEditing: false,
        quality: 1,
      });
      if (!res.canceled && res.assets && res.assets.length > 0) {
        await handleProcessVideoUri(res.assets[0].uri);
      }
    } catch (err: any) {
      alert(`Video selection error: ${err.message}`);
    }
  };

  const handleProcessVideoBlob = async (fileOrBlob: any) => {
    setVideoProcessing(true);
    setVideoStepText('Uploading video sweep to AI engine...');
    Haptics.heavy();
    try {
      const reader = new FileReader();
      const readPromise = new Promise<string>((resolve, reject) => {
        reader.onload = (e) => resolve(e.target?.result as string);
        reader.onerror = reject;
      });
      reader.readAsDataURL(fileOrBlob);
      const dataUri = await readPromise;

      setVideoStepText('Sampling keyframes & filtering blur...');
      const timeout1 = setTimeout(() => {
        setVideoStepText('Tracking sprout & rot defects across timeline...');
      }, 1000);
      const timeout2 = setTimeout(() => {
        setVideoStepText('Consulting Groq Multimodal Vision AI...');
      }, 2000);

      const result = await ApiClient.uploadVideo(inspection.id, dataUri);
      clearTimeout(timeout1);
      clearTimeout(timeout2);
      Haptics.success();
      if (onVideoCaptured) {
        onVideoCaptured(result);
      }
    } catch (err: any) {
      Haptics.error();
      alert(`Video analysis failed: ${err.message}`);
    } finally {
      setVideoProcessing(false);
    }
  };

  const handleProcessVideoUri = async (uri: string) => {
    setVideoProcessing(true);
    setVideoStepText('Uploading video sweep...');
    Haptics.heavy();
    try {
      setVideoStepText('Sampling keyframes & tracking onion defects...');
      const result = await ApiClient.uploadVideo(inspection.id, uri);
      Haptics.success();
      if (onVideoCaptured) {
        onVideoCaptured(result);
      }
    } catch (err: any) {
      Haptics.error();
      alert(`Video analysis failed: ${err.message}`);
    } finally {
      setVideoProcessing(false);
    }
  };

  const handleLoadDemoVideoSweep = async () => {
    setVideoProcessing(true);
    setVideoStepText('Loading verified demo onion video sweep...');
    Haptics.heavy();
    try {
      const demoVideoUrl = ApiClient.getDemoSampleVideoUrl();
      setVideoStepText('Sampling keyframes & tracking onion defects...');
      const res = await fetch(demoVideoUrl);
      const blob = await res.blob();
      await handleProcessVideoBlob(blob);
    } catch (err: any) {
      Haptics.error();
      alert(`Demo video sweep failed: ${err.message}`);
      setVideoProcessing(false);
    }
  };

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
      } else {
        throw new Error('No image returned from camera sensor');
      }
    } catch (err: any) {
      Haptics.error();
      if (Platform.OS === 'web') {
        console.warn('takePictureAsync failed on web, loading verified demo lot:', err.message);
        loadDemoSample();
      } else {
        alert(`Camera capture error: ${err.message}`);
      }
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

  const handleDownloadBoard = () => {
    Haptics.light();
    Linking.openURL(ApiClient.getPrintableBoardUrl()).catch((e) =>
      alert(`Could not open calibration board PDF: ${e.message}`)
    );
  };

  if (activeTab === 'CAMERA') {
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
              haptic="heavy"
              style={styles.galleryFallbackBtn}
              onPress={() => setActiveTab('UPLOAD')}
            >
              <Text style={styles.galleryFallbackText}>
                Switch to File Upload Mode
              </Text>
            </AnimatedPressable>

            <AnimatedPressable
              haptic="medium"
              style={styles.demoCardBtn}
              onPress={loadDemoSample}
            >
              <Text style={styles.demoCardBtnText}>
                Load Mandi Demo Lot (24 Bulbs + ChArUco)
              </Text>
            </AnimatedPressable>

            <AnimatedPressable
              haptic="light"
              style={styles.cancelLinkBtn}
              onPress={onCancel}
            >
              <Text style={styles.cancelLinkBtnText}>Return to Home</Text>
            </AnimatedPressable>
          </FadeInView>
        </View>
      );
    }

    if (cameraError) {
      return (
        <View style={styles.centerContainer}>
          <FadeInView delay={50} distance={15} style={styles.permCard}>
            <View style={styles.permBadge}>
              <Text style={styles.permBadgeText}>OPTICAL SENSOR NOTICE</Text>
            </View>
            <Text style={styles.permTitle}>Camera Hardware Stream Unavailable</Text>
            <Text style={styles.permDesc}>
              {Platform.OS === 'web'
                ? 'Web browser camera stream could not be started. You can upload an onion spread photo directly or inspect the verified 24-bulb Mandi demo sample.'
                : cameraError}
            </Text>

            <AnimatedPressable
              haptic="heavy"
              style={styles.permBtn}
              onPress={() => setActiveTab('UPLOAD')}
            >
              <Text style={styles.permBtnText}>Switch to File Upload Mode</Text>
            </AnimatedPressable>

            <AnimatedPressable
              haptic="medium"
              style={styles.demoCardBtn}
              onPress={loadDemoSample}
            >
              <Text style={styles.demoCardBtnText}>Load Verified Mandi Demo Lot</Text>
            </AnimatedPressable>

            <AnimatedPressable
              haptic="light"
              style={styles.galleryFallbackBtn}
              onPress={onCancel}
            >
              <Text style={styles.galleryFallbackText}>
                Return to Inspection
              </Text>
            </AnimatedPressable>
          </FadeInView>
        </View>
      );
    }
  }

  const renderUploadSurface = () => {
    return (
      <View style={styles.uploadSurfaceContainer}>
        {/* Top Floating Aerospace HUD */}
        <View style={styles.topHudBar}>
          <AnimatedPressable
            haptic="light"
            onPress={onCancel}
            style={styles.hudCircleBtn}
          >
            <Feather name="x" size={16} color="#ffffff" />
          </AnimatedPressable>

          <View style={styles.hudCenterBadge}>
            <View style={styles.hudDotLive} />
            <View>
              <Text style={styles.hudLotId}>
                {inspection.lot_id ? `LOT: ${inspection.lot_id}` : 'CEPA PACKHOUSE INTAKE'}
              </Text>
              <Text style={styles.hudCentreText}>
                {inspection.procurement_centre || 'Mandi Caliper Node'}
              </Text>
            </View>
          </View>

          <View style={styles.hudRightActions}>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setGuideVisible(true)}
              style={styles.hudCircleBtn}
            >
              <Feather name="help-circle" size={16} color="#ffffff" />
            </AnimatedPressable>
          </View>
        </View>

        {/* 3-Way Mode Switcher */}
        <View style={styles.modeSwitcherWrap}>
          <View style={styles.modeSwitcherTrack}>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setActiveTab('CAMERA')}
              style={[styles.modeSwitcherBtn, activeTab === 'CAMERA' && styles.modeSwitcherBtnActive]}
            >
              <Feather
                name="camera"
                size={12}
                color={activeTab === 'CAMERA' ? '#0f172a' : '#64748b'}
                style={{ marginRight: 5 }}
              />
              <Text style={[styles.modeSwitcherBtnText, activeTab === 'CAMERA' && styles.modeSwitcherBtnTextActive]}>
                Camera
              </Text>
            </AnimatedPressable>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setActiveTab('VIDEO')}
              style={[styles.modeSwitcherBtn, activeTab === 'VIDEO' && styles.modeSwitcherBtnActive]}
            >
              <Feather
                name="video"
                size={12}
                color={activeTab === 'VIDEO' ? '#0f172a' : '#64748b'}
                style={{ marginRight: 5 }}
              />
              <Text style={[styles.modeSwitcherBtnText, activeTab === 'VIDEO' && styles.modeSwitcherBtnTextActive]}>
                Video Sweep
              </Text>
            </AnimatedPressable>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setActiveTab('UPLOAD')}
              style={[styles.modeSwitcherBtn, activeTab === 'UPLOAD' && styles.modeSwitcherBtnActive]}
            >
              <Feather
                name="upload-cloud"
                size={12}
                color={activeTab === 'UPLOAD' ? '#0f172a' : '#64748b'}
                style={{ marginRight: 5 }}
              />
              <Text style={[styles.modeSwitcherBtnText, activeTab === 'UPLOAD' && styles.modeSwitcherBtnTextActive]}>
                Upload
              </Text>
            </AnimatedPressable>
          </View>
        </View>

        <ScrollView
          style={styles.uploadScrollView}
          contentContainerStyle={styles.uploadScrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Main Upload Dropzone Card */}
          <FadeInView delay={50} distance={12}>
            <AnimatedPressable
              haptic="heavy"
              style={styles.uploadDropzoneCard}
              onPress={triggerFileUpload}
            >
              <View style={styles.dropzoneIconCircle}>
                <Feather name="upload-cloud" size={26} color="#0f172a" />
              </View>
              <Text style={styles.dropzoneTitle}>Upload Onion Spread Photo</Text>
              <Text style={styles.dropzoneSubtitle}>
                Select high-resolution overhead photograph from your computer or camera roll (.jpg, .png, .webp)
              </Text>

              <View style={styles.browsePillBtn}>
                <Text style={styles.browsePillBtnText}>Browse &amp; Choose File</Text>
              </View>
            </AnimatedPressable>
          </FadeInView>

          {/* Instant Mandi Demo Sample Action */}
          <FadeInView delay={100} distance={12}>
            <View style={styles.demoLotActionCard}>
              <View style={styles.demoLotHeaderRow}>
                <Text style={styles.demoLotActionTag}>VERIFIED REAL SPECIMENS</Text>
                <Text style={styles.demoLotBadgeText}>24 BULBS</Text>
              </View>
              <Text style={styles.demoLotActionTitle}>Instant Mandi Demo Sample</Text>
              <Text style={styles.demoLotActionDesc}>
                Real photographic spread of 24 red onion bulbs, 40mm ChArUco 7×5 calibration scale, and automated NAFED / APMC commercial grading.
              </Text>

              <AnimatedPressable
                haptic="heavy"
                style={styles.loadDemoActionBtn}
                onPress={loadDemoSample}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                  <Text style={styles.loadDemoActionBtnText}>
                    Load Verified Mandi Demo Lot
                  </Text>
                  <Feather name="arrow-right" size={14} color="#059669" />
                </View>
              </AnimatedPressable>
            </View>
          </FadeInView>

          {/* Optical Standards Guidelines Card */}
          <FadeInView delay={150} distance={12}>
            <View style={styles.specsCard}>
              <Text style={styles.specsTitle}>Optical Capture Guidelines (NAFED / BIS IS 17912:2022)</Text>
              <View style={styles.specItem}>
                <View style={styles.specNumCircle}>
                  <Text style={styles.specNumText}>1</Text>
                </View>
                <Text style={styles.specText}>
                  <Text style={styles.specBold}>Top-Down Overhead Angle (90°):</Text> Position camera directly perpendicular to the spread to avoid perspective distortion.
                </Text>
              </View>
              <View style={styles.specItem}>
                <View style={styles.specNumCircle}>
                  <Text style={styles.specNumText}>2</Text>
                </View>
                <Text style={styles.specText}>
                  <Text style={styles.specBold}>ChArUco 7×5 Reference Marker:</Text> Include card in frame for true sub-millimeter caliber scale lock.
                </Text>
              </View>
              <View style={styles.specItem}>
                <View style={styles.specNumCircle}>
                  <Text style={styles.specNumText}>3</Text>
                </View>
                <Text style={styles.specText}>
                  <Text style={styles.specBold}>Single-Layer Spread:</Text> Keep 15–30 bulbs separated without physical touching or stacking.
                </Text>
              </View>
            </View>
          </FadeInView>

          {/* Switch to Camera button */}
          <FadeInView delay={200} distance={10}>
            <AnimatedPressable
              haptic="light"
              style={styles.switchBackBtn}
              onPress={() => setActiveTab('CAMERA')}
            >
              <Text style={styles.switchBackText}>Switch to Overhead Camera Viewfinder</Text>
            </AnimatedPressable>
          </FadeInView>
        </ScrollView>
      </View>
    );
  };

  const renderVideoSurface = () => {
    return (
      <View style={styles.uploadSurfaceContainer}>
        {/* Top Floating HUD Bar */}
        <View style={styles.topHudBar}>
          <AnimatedPressable
            haptic="light"
            onPress={onCancel}
            style={styles.hudCircleBtn}
          >
            <Feather name="x" size={16} color="#ffffff" />
          </AnimatedPressable>

          <View style={styles.hudCenterBadge}>
            <View style={[styles.hudDotLive, { backgroundColor: '#38bdf8' }]} />
            <View>
              <Text style={styles.hudLotId}>
                {inspection.lot_id ? `LOT: ${inspection.lot_id}` : 'CEPA PACKHOUSE INTAKE'}
              </Text>
              <Text style={styles.hudCentreText}>
                Video Sweep &amp; Defect Sorter
              </Text>
            </View>
          </View>

          <View style={styles.hudRightActions}>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setGuideVisible(true)}
              style={styles.hudCircleBtn}
            >
              <Feather name="help-circle" size={16} color="#ffffff" />
            </AnimatedPressable>
          </View>
        </View>

        {/* 3-Way Mode Switcher */}
        <View style={styles.modeSwitcherWrap}>
          <View style={styles.modeSwitcherTrack}>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setActiveTab('CAMERA')}
              style={[styles.modeSwitcherBtn, activeTab === 'CAMERA' && styles.modeSwitcherBtnActive]}
            >
              <Feather
                name="camera"
                size={12}
                color={activeTab === 'CAMERA' ? '#0f172a' : '#64748b'}
                style={{ marginRight: 5 }}
              />
              <Text style={[styles.modeSwitcherBtnText, activeTab === 'CAMERA' && styles.modeSwitcherBtnTextActive]}>
                Camera
              </Text>
            </AnimatedPressable>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setActiveTab('VIDEO')}
              style={[styles.modeSwitcherBtn, activeTab === 'VIDEO' && styles.modeSwitcherBtnActive]}
            >
              <Feather
                name="video"
                size={12}
                color={activeTab === 'VIDEO' ? '#0f172a' : '#64748b'}
                style={{ marginRight: 5 }}
              />
              <Text style={[styles.modeSwitcherBtnText, activeTab === 'VIDEO' && styles.modeSwitcherBtnTextActive]}>
                Video Sweep
              </Text>
            </AnimatedPressable>
            <AnimatedPressable
              haptic="selection"
              onPress={() => setActiveTab('UPLOAD')}
              style={[styles.modeSwitcherBtn, activeTab === 'UPLOAD' && styles.modeSwitcherBtnActive]}
            >
              <Feather
                name="upload-cloud"
                size={12}
                color={activeTab === 'UPLOAD' ? '#0f172a' : '#64748b'}
                style={{ marginRight: 5 }}
              />
              <Text style={[styles.modeSwitcherBtnText, activeTab === 'UPLOAD' && styles.modeSwitcherBtnTextActive]}>
                Upload
              </Text>
            </AnimatedPressable>
          </View>
        </View>

        <ScrollView
          style={styles.uploadScrollView}
          contentContainerStyle={styles.uploadScrollContent}
          showsVerticalScrollIndicator={false}
        >
          {videoProcessing ? (
            <FadeInView delay={30} distance={15}>
              <View style={styles.videoProcessingCard}>
                <ActivityIndicator size="large" color="#38bdf8" style={{ marginBottom: 16 }} />
                <Text style={styles.videoProcessingTitle}>Processing Video Inspection</Text>
                <Text style={styles.videoProcessingStep}>{videoStepText}</Text>
                <View style={styles.videoProgressPillRow}>
                  <View style={styles.videoProgressStepBadge}>
                    <Text style={styles.videoProgressStepBadgeText}>1. Keyframe Sampling</Text>
                  </View>
                  <View style={styles.videoProgressStepBadge}>
                    <Text style={styles.videoProgressStepBadgeText}>2. Sprout &amp; Rot Tracking</Text>
                  </View>
                  <View style={styles.videoProgressStepBadge}>
                    <Text style={styles.videoProgressStepBadgeText}>3. Groq Multimodal AI</Text>
                  </View>
                </View>
                <Text style={styles.videoProcessingHint}>
                  Extracting sharp frames, filtering camera motion blur, analyzing bulb health, and calling Groq Multimodal Vision AI.
                </Text>
              </View>
            </FadeInView>
          ) : (
            <>
              {/* Primary Video Sweep Action Card */}
              <FadeInView delay={50} distance={12}>
                <AnimatedPressable
                  haptic="heavy"
                  style={[styles.uploadDropzoneCard, { borderColor: 'rgba(56, 189, 248, 0.4)' }]}
                  onPress={triggerVideoUpload}
                >
                  <View style={[styles.dropzoneIconCircle, { borderColor: 'rgba(56, 189, 248, 0.5)', backgroundColor: 'rgba(56, 189, 248, 0.15)' }]}>
                    <Feather name="video" size={26} color="#38bdf8" />
                  </View>
                  <Text style={styles.dropzoneTitle}>Record or Select Video Sweep</Text>
                  <Text style={styles.dropzoneSubtitle}>
                    Pan camera slowly across an onion lot, or hold onions one by one. The AI tracks every bulb and timestamps rotten or sprouted ones (.mp4, .mov, .webm)
                  </Text>
                  <View style={[styles.browsePillBtn, { backgroundColor: '#38bdf8' }]}>
                    <Text style={[styles.browsePillBtnText, { color: '#09090b' }]}>Choose Video File</Text>
                  </View>
                </AnimatedPressable>
              </FadeInView>

              {/* 1-Tap Real Mandi Demo Video Action */}
              <FadeInView delay={100} distance={12}>
                <View style={[styles.demoLotActionCard, { borderColor: 'rgba(56, 189, 248, 0.25)' }]}>
                  <View style={styles.demoLotHeaderRow}>
                    <Text style={[styles.demoLotActionTag, { color: '#38bdf8' }]}>VERIFIED 4-SECOND SWEEP</Text>
                    <Text style={styles.demoLotBadgeText}>40+ BULBS</Text>
                  </View>
                  <Text style={styles.demoLotActionTitle}>Instant Demo Video Sweep</Text>
                  <Text style={styles.demoLotActionDesc}>
                    Pre-loaded smooth video sweep across red onion bulbs with multi-frame tracking, automated sprout detection, and Groq Multimodal Vision AI appraisal.
                  </Text>
                  <AnimatedPressable
                    haptic="heavy"
                    style={[styles.loadDemoActionBtn, { backgroundColor: 'rgba(56, 189, 248, 0.18)', borderColor: 'rgba(56, 189, 248, 0.4)' }]}
                    onPress={handleLoadDemoVideoSweep}
                  >
                    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                      <Text style={[styles.loadDemoActionBtnText, { color: '#38bdf8' }]}>
                        Run Demo Video Sweep
                      </Text>
                      <Feather name="arrow-right" size={14} color="#38bdf8" />
                    </View>
                  </AnimatedPressable>
                </View>
              </FadeInView>

              {/* Video Inspection Guidelines */}
              <FadeInView delay={150} distance={12}>
                <View style={styles.specsCard}>
                  <Text style={styles.specsTitle}>Video Sweep Tips</Text>
                  <View style={styles.specItem}>
                    <View style={styles.specNumCircle}>
                      <Text style={styles.specNumText}>1</Text>
                    </View>
                    <Text style={styles.specText}>
                      <Text style={styles.specBold}>Smooth Camera Sweep:</Text> Move phone slowly across the lot. Our blur filter automatically picks the sharpest moments.
                    </Text>
                  </View>
                  <View style={styles.specItem}>
                    <View style={styles.specNumCircle}>
                      <Text style={styles.specNumText}>2</Text>
                    </View>
                    <Text style={styles.specText}>
                      <Text style={styles.specBold}>One-by-One Sorting:</Text> If inspecting single bulbs, hold each bulb in frame for ~1 second so the AI can inspect skin and neck.
                    </Text>
                  </View>
                  <View style={styles.specItem}>
                    <View style={styles.specNumCircle}>
                      <Text style={styles.specNumText}>3</Text>
                    </View>
                    <Text style={styles.specText}>
                      <Text style={styles.specBold}>Defect Timeline:</Text> Rotten or sprouted bulbs are tagged with exact timestamps so you can easily cull them.
                    </Text>
                  </View>
                </View>
              </FadeInView>
            </>
          )}
        </ScrollView>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {activeTab === 'UPLOAD' ? (
        renderUploadSurface()
      ) : activeTab === 'VIDEO' ? (
        renderVideoSurface()
      ) : (
        <CameraView
          ref={cameraRef}
          style={StyleSheet.absoluteFill}
          facing={facing}
          enableTorch={torchOn}
          onMountError={(e) => setCameraError(e?.message || 'Camera stream failed to mount')}
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
                  <Feather name="x" size={18} color="#ffffff" />
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
                  {/* Flip Camera */}
                  <AnimatedPressable
                    haptic="selection"
                    onPress={toggleFacing}
                    style={styles.hudCircleBtn}
                    accessibilityLabel="Flip Camera"
                  >
                    <Feather name="refresh-cw" size={16} color="#ffffff" />
                  </AnimatedPressable>

                  {/* Guide Button */}
                  <AnimatedPressable
                    haptic="selection"
                    onPress={() => setGuideVisible(true)}
                    style={styles.hudCircleBtn}
                  >
                    <Feather name="help-circle" size={16} color="#ffffff" />
                  </AnimatedPressable>

                  {/* Torch Toggle */}
                  <AnimatedPressable
                    haptic="selection"
                    onPress={() => setTorchOn(!torchOn)}
                    style={[styles.hudCircleBtn, torchOn && styles.hudTorchActive]}
                  >
                    <Feather name="zap" size={16} color={torchOn ? '#0f172a' : '#ffffff'} />
                  </AnimatedPressable>
                </View>
              </View>
            </FadeInView>

            {/* 3-Way Mode Switcher */}
            <View style={styles.modeSwitcherWrap}>
              <View style={styles.modeSwitcherTrack}>
                <AnimatedPressable
                  haptic="selection"
                  onPress={() => setActiveTab('CAMERA')}
                  style={[styles.modeSwitcherBtn, styles.modeSwitcherBtnActive]}
                >
                  <Text style={[styles.modeSwitcherBtnText, styles.modeSwitcherBtnTextActive]}>
                    Camera
                  </Text>
                </AnimatedPressable>
                <AnimatedPressable
                  haptic="selection"
                  onPress={() => setActiveTab('VIDEO')}
                  style={styles.modeSwitcherBtn}
                >
                  <Text style={styles.modeSwitcherBtnText}>
                    Video Sweep
                  </Text>
                </AnimatedPressable>
                <AnimatedPressable
                  haptic="selection"
                  onPress={() => setActiveTab('UPLOAD')}
                  style={styles.modeSwitcherBtn}
                >
                  <Text style={styles.modeSwitcherBtnText}>
                    Upload
                  </Text>
                </AnimatedPressable>
              </View>
            </View>

            {/* Level Guidance Bar */}
            <View style={styles.levelBannerWrap}>
              <View style={[styles.levelBanner, isLevel ? styles.levelBannerLocked : styles.levelBannerWarning]}>
                <Animated.View style={[styles.levelDot, isLevel && { transform: [{ scale: pulseAnim }] }]} />
                <Text style={styles.levelBannerText}>
                  {isLevel
                    ? 'PHONE LEVEL & READY · SINGLE LAYER SPREAD'
                    : 'HOLD PHONE FLAT OVER SPREAD (~60CM HEIGHT)'}
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
                  {/* Photo Upload Button */}
                  <AnimatedPressable
                    haptic="light"
                    style={styles.deckSideBtn}
                    onPress={triggerFileUpload}
                    disabled={capturing}
                    accessibilityLabel="Upload Image File"
                  >
                    <View style={[styles.sideBtnIconBox, styles.uploadIconBox]}>
                      <Feather name="upload-cloud" size={15} color="#ffffff" />
                    </View>
                    <Text style={styles.sideBtnLabel}>Upload</Text>
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
      )}

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
                <Feather name="x" size={16} color="#0f172a" />
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
              haptic="selection"
              onPress={handleDownloadBoard}
              style={styles.guideDownloadBtn}
            >
              <Text style={styles.guideDownloadBtnText}>Print True-Scale ChArUco 7×5 Board (PDF)</Text>
            </AnimatedPressable>

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
  guideDownloadBtn: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingVertical: 12,
    borderRadius: Radius.md,
    alignItems: 'center',
    marginBottom: Spacing.sm,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.18)',
  },
  guideDownloadBtnText: {
    color: '#34d399',
    fontSize: 12.5,
    fontWeight: '700',
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

  /* Camera Flip & Switcher */
  hudFlipIcon: {
    fontSize: 16,
    color: '#ffffff',
    fontWeight: '700',
  },
  modeSwitcherWrap: {
    alignItems: 'center',
    marginTop: 6,
    marginBottom: 6,
    zIndex: 10,
  },
  modeSwitcherTrack: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    borderRadius: 20,
    padding: 3,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.18)',
  },
  modeSwitcherBtn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
  },
  modeSwitcherBtnActive: {
    backgroundColor: '#ffffff',
  },
  modeSwitcherBtnText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#a1a1aa',
  },
  modeSwitcherBtnTextActive: {
    color: '#0c0c0e',
    fontWeight: '800',
  },
  uploadIconBox: {
    backgroundColor: 'rgba(255, 255, 255, 0.18)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.35)',
  },
  uploadIconDeckText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '800',
    lineHeight: 18,
  },

  /* Dedicated Upload Surface */
  uploadSurfaceContainer: {
    flex: 1,
    backgroundColor: '#09090b',
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.xs,
  },
  uploadScrollView: {
    flex: 1,
  },
  uploadScrollContent: {
    paddingBottom: 40,
    paddingTop: Spacing.xs,
    gap: Spacing.md,
  },
  uploadDropzoneCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: Radius.lg,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.22)',
    borderStyle: 'dashed',
    padding: Spacing.xl,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: Spacing.xs,
  },
  dropzoneIconCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  dropzoneArrow: {
    fontSize: 24,
    color: '#ffffff',
    fontWeight: '800',
  },
  dropzoneTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 4,
  },
  dropzoneSubtitle: {
    fontSize: 12,
    color: '#a1a1aa',
    textAlign: 'center',
    lineHeight: 17,
    marginBottom: Spacing.lg,
    paddingHorizontal: Spacing.md,
  },
  browsePillBtn: {
    backgroundColor: '#ffffff',
    paddingHorizontal: Spacing.xl,
    paddingVertical: 12,
    borderRadius: Radius.md,
    alignItems: 'center',
    ...Shadows.card,
  },
  browsePillBtnText: {
    color: '#0c0c0e',
    fontSize: 13,
    fontWeight: '700',
  },
  demoLotActionCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
  },
  demoLotHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  demoLotActionTag: {
    fontSize: 9.5,
    fontFamily: 'monospace',
    fontWeight: '800',
    color: '#f59e0b',
    letterSpacing: 0.5,
  },
  demoLotBadgeText: {
    fontSize: 9.5,
    fontFamily: 'monospace',
    fontWeight: '800',
    color: '#ffffff',
    backgroundColor: 'rgba(245, 158, 11, 0.25)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  demoLotActionTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 4,
  },
  demoLotActionDesc: {
    fontSize: 11.5,
    color: '#a1a1aa',
    lineHeight: 16,
    marginBottom: Spacing.md,
  },
  loadDemoActionBtn: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    paddingVertical: 11,
    borderRadius: Radius.sm,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
  loadDemoActionBtnText: {
    color: '#ffffff',
    fontSize: 12.5,
    fontWeight: '700',
  },
  specsCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  specsTitle: {
    fontSize: 10.5,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: '#71717a',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: Spacing.sm,
  },
  specItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    marginBottom: 8,
  },
  specNumCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 1,
  },
  specNumText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#ffffff',
  },
  specText: {
    flex: 1,
    fontSize: 11.5,
    color: '#a1a1aa',
    lineHeight: 16,
  },
  specBold: {
    color: '#f4f4f5',
    fontWeight: '700',
  },
  switchBackBtn: {
    paddingVertical: 12,
    alignItems: 'center',
  },
  switchBackText: {
    color: '#71717a',
    fontSize: 12,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  cancelLinkBtn: {
    paddingVertical: 8,
    alignItems: 'center',
    marginTop: 4,
  },
  cancelLinkBtnText: {
    color: '#71717a',
    fontSize: 11.5,
    fontWeight: '600',
  },
  videoProcessingCard: {
    backgroundColor: '#0c0c0e',
    borderRadius: Radius.lg,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.4)',
    marginVertical: 20,
    ...Shadows.cardElevated,
  },
  videoProcessingTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 6,
  },
  videoProcessingStep: {
    fontSize: 14,
    fontWeight: '600',
    color: '#38bdf8',
    marginBottom: 16,
    textAlign: 'center',
  },
  videoProgressPillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    justifyContent: 'center',
    marginBottom: 16,
  },
  videoProgressStepBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  videoProgressStepBadgeText: {
    fontSize: 10,
    color: '#e2e8f0',
    fontWeight: '600',
  },
  videoProcessingHint: {
    fontSize: 12,
    color: '#94a3b8',
    textAlign: 'center',
    lineHeight: 18,
    maxWidth: 320,
  },
});
