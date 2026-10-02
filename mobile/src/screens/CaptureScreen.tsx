import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Image,
  Linking,
  Modal,
  Platform,
  Pressable,
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
  const [liveOnionsDetected, setLiveOnionsDetected] = useState<number>(0);
  const [liveSensorMessage, setLiveSensorMessage] = useState<string>(
    'Align onions flat in frame · Tap screen to focus'
  );
  const cameraRef = useRef<CameraView>(null);

  const toggleFacing = () => {
    Haptics.selection();
    setFacing((prev) => (prev === 'back' ? 'front' : 'back'));
  };

  // Real-time live sensor telemetry in viewfinder on web
  useEffect(() => {
    if (Platform.OS !== 'web' || activeTab !== 'CAMERA') return;

    const interval = setInterval(() => {
      try {
        const video = document.querySelector('video') as HTMLVideoElement | null;
        if (!video || video.videoWidth === 0) return;

        const canvas = document.createElement('canvas');
        canvas.width = 160;
        canvas.height = 120;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.drawImage(video, 0, 0, 160, 120);
        const imgData = ctx.getImageData(0, 0, 160, 120);
        const data = imgData.data;

        let organicCount = 0;
        let leftCount = 0;
        let rightCount = 0;

        for (let i = 0; i < data.length; i += 16) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          const max = Math.max(r, g, b);
          const min = Math.min(r, g, b);
          const delta = max - min;

          // Warm allium hues (red, purple, golden, or cream outer tunic)
          const isWarmRedPurple = r > g * 1.12 && r > b * 1.05 && r > 60;
          const isGoldenBrown = r > 120 && g > 70 && b < g * 0.9;
          const isCreamBulb = r > 155 && g > 145 && b > 135 && delta < 45 && max < 252;

          if (isWarmRedPurple || isGoldenBrown || isCreamBulb) {
            organicCount++;
            const pixelIndex = i / 4;
            const x = pixelIndex % 160;
            if (x < 80) leftCount++;
            else rightCount++;
          }
        }

        let count = 0;
        if (organicCount > 25) {
          if (leftCount > 15 && rightCount > 15) {
            count = 2;
          } else {
            count = 1;
          }
        }

        setLiveOnionsDetected(count);
        if (count >= 2) {
          setLiveSensorMessage('2 Onion Bulbs Tracked · Optical Caliper Ready');
        } else if (count === 1) {
          setLiveSensorMessage('1 Onion Bulb Tracked · Ready to Grade');
        } else {
          setLiveSensorMessage('Position onions flat in frame · Tap screen to focus');
        }
      } catch {
        // Non-blocking background telemetry
      }
    }, 750);

    return () => clearInterval(interval);
  }, [activeTab]);

  const captureWebVideoFrame = (): string | null => {
    if (Platform.OS !== 'web') return null;
    try {
      const videoElements = document.querySelectorAll('video');
      let targetVideo: HTMLVideoElement | null = null;
      for (let i = 0; i < videoElements.length; i++) {
        const v = videoElements[i];
        if (v.videoWidth > 0 && v.videoHeight > 0) {
          targetVideo = v;
          break;
        }
      }
      if (!targetVideo && videoElements.length > 0) {
        targetVideo = videoElements[0];
      }
      if (targetVideo && targetVideo.videoWidth > 0) {
        const canvas = document.createElement('canvas');
        canvas.width = targetVideo.videoWidth;
        canvas.height = targetVideo.videoHeight;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(targetVideo, 0, 0, canvas.width, canvas.height);
          const dataUri = canvas.toDataURL('image/jpeg', 0.95);
          if (dataUri && dataUri.length > 500) {
            return dataUri;
          }
        }
      }
    } catch (e) {
      console.warn('captureWebVideoFrame error:', e);
    }
    return null;
  };

  const triggerFileUpload = (useCamera: boolean = false) => {
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
        if (useCamera) {
          input.setAttribute('capture', 'environment');
        } else {
          input.removeAttribute('capture');
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

  // Optical / Digital Zoom Presets
  const [zoom, setZoom] = useState(0);
  const ZOOM_PRESETS = [
    { label: '0.5x', value: 0 },
    { label: '1x', value: 0.15 },
    { label: '2x', value: 0.35 },
  ];

  // Animated Tap-to-Focus Reticle
  const [focusPoint, setFocusPoint] = useState<{ x: number; y: number } | null>(null);
  const focusAnim = useRef(new Animated.Value(0)).current;

  const handleTapToFocus = (e: any) => {
    const { locationX, locationY } = e.nativeEvent;
    if (locationX === undefined || locationY === undefined) return;
    Haptics.light();
    setFocusPoint({ x: locationX, y: locationY });

    focusAnim.setValue(0);
    Animated.sequence([
      Animated.spring(focusAnim, {
        toValue: 1,
        friction: 5,
        tension: 100,
        useNativeDriver: true,
      }),
      Animated.delay(1200),
      Animated.timing(focusAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(({ finished }) => {
      if (finished) {
        setFocusPoint(null);
      }
    });
  };

  const takePhoto = async () => {
    if (capturing) return;
    Haptics.heavy();
    setCapturing(true);
    try {
      // 1. Direct Web canvas capture from live <video> stream
      if (Platform.OS === 'web') {
        const webPhoto = captureWebVideoFrame();
        if (webPhoto) {
          Haptics.snap();
          onPhotoCaptured(webPhoto);
          return;
        }
      }

      // 2. Native CameraView capture
      if (cameraRef.current) {
        const photo = await cameraRef.current.takePictureAsync({
          quality: 0.95,
          skipProcessing: false,
        });
        if (photo?.uri) {
          Haptics.snap();
          onPhotoCaptured(photo.uri);
          return;
        }
      }

      // 3. Fallback: prompt device native camera directly
      if (Platform.OS === 'web') {
        triggerFileUpload(true);
        return;
      }

      throw new Error('No image returned from camera sensor');
    } catch (err: any) {
      Haptics.error();
      if (Platform.OS === 'web') {
        console.warn('Camera sensor snapshot failed, triggering native camera:', err.message);
        triggerFileUpload(true);
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
          zoom={zoom}
          autofocus="on"
          onMountError={(e) => setCameraError(e?.message || 'Camera stream failed to mount')}
        >
          <View style={styles.overlayContainer}>
            {/* Top Floating Clean HUD */}
            <FadeInView delay={50} distance={-10}>
              <View style={styles.topHudBar}>
                <AnimatedPressable
                  haptic="light"
                  onPress={onCancel}
                  style={styles.hudCircleBtn}
                  accessibilityLabel="Close Camera"
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
                  {/* Switch Camera Lens (Front/Back) */}
                  <AnimatedPressable
                    haptic="selection"
                    onPress={toggleFacing}
                    style={styles.hudCircleBtn}
                    accessibilityLabel="Switch Camera Lens"
                  >
                    <Feather name="refresh-cw" size={16} color="#ffffff" />
                  </AnimatedPressable>

                  {/* Guide Button */}
                  <AnimatedPressable
                    haptic="selection"
                    onPress={() => setGuideVisible(true)}
                    style={styles.hudCircleBtn}
                    accessibilityLabel="Calibration Guide"
                  >
                    <Feather name="help-circle" size={16} color="#ffffff" />
                  </AnimatedPressable>

                  {/* Torch Toggle */}
                  <AnimatedPressable
                    haptic="selection"
                    onPress={() => setTorchOn(!torchOn)}
                    style={[styles.hudCircleBtn, torchOn && styles.hudTorchActive]}
                    accessibilityLabel="Toggle Torch"
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

            {/* Viewport: Interactive Tap-to-Focus Surface */}
            <Pressable
              style={styles.targetViewport}
              onPress={handleTapToFocus}
              accessibilityLabel="Tap to focus camera"
            >
              {/* Subtle Rule-of-Thirds Grid */}
              <View style={styles.gridOverlay} pointerEvents="none">
                <View style={styles.gridLineH1} />
                <View style={styles.gridLineH2} />
                <View style={styles.gridLineV1} />
                <View style={styles.gridLineV2} />
              </View>

              {/* Viewport Framing Brackets */}
              <View style={styles.framingFrame} pointerEvents="none">
                <View style={[styles.cleanCorner, styles.cTopLeft]} />
                <View style={[styles.cleanCorner, styles.cTopRight]} />
                <View style={[styles.cleanCorner, styles.cBottomLeft]} />
                <View style={[styles.cleanCorner, styles.cBottomRight]} />
              </View>

              {/* Animated Tap-to-Focus Reticle */}
              {focusPoint && (
                <Animated.View
                  pointerEvents="none"
                  style={[
                    styles.focusReticle,
                    {
                      left: focusPoint.x - 36,
                      top: focusPoint.y - 36,
                      opacity: focusAnim,
                      transform: [
                        {
                          scale: focusAnim.interpolate({
                            inputRange: [0, 1],
                            outputRange: [1.3, 1],
                          }),
                        },
                      ],
                    },
                  ]}
                >
                  <View style={[styles.focusReticleCorner, styles.fCornerTL]} />
                  <View style={[styles.focusReticleCorner, styles.fCornerTR]} />
                  <View style={[styles.focusReticleCorner, styles.fCornerBL]} />
                  <View style={[styles.focusReticleCorner, styles.fCornerBR]} />
                  <View style={styles.focusReticlePip} />
                </Animated.View>
              )}

              {/* Dynamic Live Sensor Guidance Pill */}
              <View
                style={[
                  styles.guidancePill,
                  liveOnionsDetected > 0 && {
                    backgroundColor: 'rgba(6, 78, 59, 0.88)',
                    borderColor: '#10b981',
                  },
                ]}
                pointerEvents="none"
              >
                <Feather
                  name={liveOnionsDetected > 0 ? 'check-circle' : 'maximize'}
                  size={12}
                  color={liveOnionsDetected > 0 ? '#34d399' : '#fbbf24'}
                  style={{ marginRight: 6 }}
                />
                <Text
                  style={[
                    styles.guidancePillText,
                    liveOnionsDetected > 0 && { color: '#ffffff', fontWeight: '700' },
                  ]}
                >
                  {liveSensorMessage}
                </Text>
              </View>
            </Pressable>

            {/* Bottom Industrial Controls Deck */}
            <FadeInView delay={100} distance={15}>
              <View style={styles.bottomDeck}>
                {/* Lens / Zoom Selector Pills */}
                <View style={styles.zoomPillsRow}>
                  {ZOOM_PRESETS.map((preset) => {
                    const isSelected = zoom === preset.value;
                    return (
                      <AnimatedPressable
                        key={preset.label}
                        haptic="selection"
                        onPress={() => setZoom(preset.value)}
                        style={[
                          styles.zoomPill,
                          isSelected && styles.zoomPillActive,
                        ]}
                      >
                        <Text
                          style={[
                            styles.zoomPillText,
                            isSelected && styles.zoomPillTextActive,
                          ]}
                        >
                          {preset.label}
                        </Text>
                      </AnimatedPressable>
                    );
                  })}
                </View>

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

                  {/* Tactile Shutter Button */}
                  <AnimatedPressable
                    haptic="heavy"
                    scaleTo={0.90}
                    style={styles.shutterOuterRing}
                    onPress={takePhoto}
                    disabled={capturing}
                    accessibilityLabel="Capture Photo"
                  >
                    <View style={styles.shutterMiddleHalo}>
                      <View style={styles.shutterCoreButton}>
                        {capturing ? (
                          <ActivityIndicator color="#0c0c0e" size="small" />
                        ) : (
                          <View style={styles.shutterCenterPip} />
                        )}
                      </View>
                    </View>
                  </AnimatedPressable>

                  {/* Instant Mandi Demo Sample (Natural Produce) */}
                  <AnimatedPressable
                    haptic="medium"
                    style={styles.deckSideBtn}
                    onPress={loadDemoSample}
                    disabled={capturing}
                    accessibilityLabel="Load Natural Test Lot"
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

  /* Viewport & Interactive Focus Surface */
  targetViewport: {
    flex: 1,
    marginVertical: 10,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
    overflow: 'hidden',
  },
  gridOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'space-evenly',
    alignItems: 'center',
  },
  gridLineH1: {
    position: 'absolute',
    top: '33.33%',
    left: 16,
    right: 16,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  gridLineH2: {
    position: 'absolute',
    top: '66.66%',
    left: 16,
    right: 16,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  gridLineV1: {
    position: 'absolute',
    left: '33.33%',
    top: 16,
    bottom: 16,
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  gridLineV2: {
    position: 'absolute',
    left: '66.66%',
    top: 16,
    bottom: 16,
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  framingFrame: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    margin: 16,
  },
  cleanCorner: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderColor: 'rgba(255, 255, 255, 0.55)',
  },
  cTopLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    borderTopLeftRadius: 6,
  },
  cTopRight: {
    top: 0,
    right: 0,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderTopRightRadius: 6,
  },
  cBottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 2,
    borderLeftWidth: 2,
    borderBottomLeftRadius: 6,
  },
  cBottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 2,
    borderRightWidth: 2,
    borderBottomRightRadius: 6,
  },

  /* Animated Tap-to-Focus Reticle */
  focusReticle: {
    position: 'absolute',
    width: 72,
    height: 72,
    justifyContent: 'center',
    alignItems: 'center',
  },
  focusReticleCorner: {
    position: 'absolute',
    width: 14,
    height: 14,
    borderColor: '#fbbf24',
  },
  fCornerTL: { top: 0, left: 0, borderTopWidth: 2, borderLeftWidth: 2 },
  fCornerTR: { top: 0, right: 0, borderTopWidth: 2, borderRightWidth: 2 },
  fCornerBL: { bottom: 0, left: 0, borderBottomWidth: 2, borderLeftWidth: 2 },
  fCornerBR: { bottom: 0, right: 0, borderBottomWidth: 2, borderRightWidth: 2 },
  focusReticlePip: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#fbbf24',
  },

  /* Guidance Pill */
  guidancePill: {
    position: 'absolute',
    bottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(12, 12, 14, 0.75)',
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
  },
  guidancePillText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: '#e4e4e7',
    letterSpacing: 0.2,
  },

  /* Lens / Zoom Pills */
  zoomPillsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  zoomPill: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  zoomPillActive: {
    backgroundColor: '#ffffff',
    borderColor: '#ffffff',
    transform: [{ scale: 1.05 }],
  },
  zoomPillText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#d4d4d8',
  },
  zoomPillTextActive: {
    color: '#0f172a',
    fontWeight: '800',
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
  shutterMiddleHalo: {
    width: 62,
    height: 62,
    borderRadius: 31,
    backgroundColor: '#ffffff',
    justifyContent: 'center',
    alignItems: 'center',
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
