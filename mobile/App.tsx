import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Platform,
  SafeAreaView,
  StatusBar,
  StyleSheet,
  View,
} from 'react-native';
import { ApiClient } from './src/api/client';
import { Header } from './src/components/Header';
import { CaptureScreen } from './src/screens/CaptureScreen';
import { FinalReportScreen } from './src/screens/FinalReportScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { NewInspectionScreen } from './src/screens/NewInspectionScreen';
import { QualityCheckScreen } from './src/screens/QualityCheckScreen';
import { ResultsScreen } from './src/screens/ResultsScreen';
import { InspectionDetail, SampleDetail, VideoScanResult } from './src/types';
import { Colors } from './src/ui';

type Screen =
  | 'HOME'
  | 'NEW_INSPECTION'
  | 'CAPTURE'
  | 'QUALITY_CHECK'
  | 'RESULTS'
  | 'FINAL_REPORT';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('HOME');
  const [activeInspection, setActiveInspection] = useState<InspectionDetail | null>(null);
  const [activeSample, setActiveSample] = useState<SampleDetail | null>(null);
  const [activeVideoResult, setActiveVideoResult] = useState<VideoScanResult | null>(null);
  const [capturedPhotoUri, setCapturedPhotoUri] = useState<string | null>(null);
  const [captureInitialTab, setCaptureInitialTab] = useState<'CAMERA' | 'UPLOAD' | 'VIDEO'>('CAMERA');

  const [serverOnline, setServerOnline] = useState(true);
  const [policyVersion, setPolicyVersion] = useState('BIS_IS_17912_2022');
  const [isMockActive, setIsMockActive] = useState(false);

  // Smooth Screen Cross-fade
  const screenFade = useRef(new Animated.Value(1)).current;

  const navigateTo = (screen: Screen) => {
    Animated.sequence([
      Animated.timing(screenFade, {
        toValue: 0.85,
        duration: 80,
        useNativeDriver: true,
      }),
      Animated.timing(screenFade, {
        toValue: 1,
        duration: 160,
        useNativeDriver: true,
      }),
    ]).start();
    setCurrentScreen(screen);
  };

  // Poll health on startup and periodically
  useEffect(() => {
    const checkServer = async () => {
      try {
        const cv = await ApiClient.checkCvHealth();
        setServerOnline(true);
        if (cv.active_policy) setPolicyVersion(cv.active_policy);
        setIsMockActive(!!cv.warning);
      } catch {
        setServerOnline(false);
      }
    };

    checkServer();
    const interval = setInterval(checkServer, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectInspection = async (id: string) => {
    try {
      const inspection = await ApiClient.getInspection(id);
      setActiveInspection(inspection);

      if (inspection.status === 'FINALIZED') {
        navigateTo('FINAL_REPORT');
      } else if (inspection.sample_ids.length > 0) {
        // Load the latest sample
        const latestSampleId = inspection.sample_ids[inspection.sample_ids.length - 1];
        const sample = await ApiClient.getSample(inspection.id, latestSampleId);
        setActiveSample(sample);
        navigateTo('RESULTS');
      } else {
        setCaptureInitialTab('CAMERA');
        navigateTo('CAPTURE');
      }
    } catch (e: any) {
      alert(`Could not load inspection: ${e.message}`);
    }
  };

  return (
    <SafeAreaView style={[styles.safeArea, currentScreen === 'CAPTURE' && styles.safeAreaCapture]}>
      <StatusBar
        barStyle={currentScreen === 'CAPTURE' ? 'light-content' : 'dark-content'}
        backgroundColor={currentScreen === 'CAPTURE' ? '#000000' : Colors.bg}
      />
      <View style={[styles.appShell, currentScreen === 'CAPTURE' && styles.appShellCapture]}>
        {currentScreen !== 'CAPTURE' && (
          <Header
            serverConnected={serverOnline}
            policyVersion={policyVersion}
            isMockActive={isMockActive}
          />
        )}

        <Animated.View style={[styles.content, { opacity: screenFade }]}>
          {currentScreen === 'HOME' && (
            <HomeScreen
              onStartNewInspection={(mode = 'CAMERA') => {
                setCaptureInitialTab(mode);
                navigateTo('NEW_INSPECTION');
              }}
              onSelectInspection={handleSelectInspection}
            />
          )}

          {currentScreen === 'NEW_INSPECTION' && (
            <NewInspectionScreen
              onInspectionCreated={(inspection, mode = 'CAMERA') => {
                setActiveInspection(inspection);
                setCaptureInitialTab(mode);
                navigateTo('CAPTURE');
              }}
              onCancel={() => navigateTo('HOME')}
            />
          )}

          {currentScreen === 'CAPTURE' && activeInspection && (
            <CaptureScreen
              inspection={activeInspection}
              initialTab={captureInitialTab}
              onPhotoCaptured={(uri) => {
                setCapturedPhotoUri(uri);
                navigateTo('QUALITY_CHECK');
              }}
              onVideoCaptured={async (videoResult) => {
                setActiveVideoResult(videoResult);
                try {
                  const s = await ApiClient.getSample(activeInspection.id, videoResult.sample_id);
                  setActiveSample(s);
                } catch (e) {
                  console.warn('Failed to load sample for video:', e);
                }
                navigateTo('RESULTS');
              }}
              onCancel={() => navigateTo('HOME')}
            />
          )}

          {currentScreen === 'QUALITY_CHECK' && activeInspection && capturedPhotoUri && (
            <QualityCheckScreen
              inspection={activeInspection}
              photoUri={capturedPhotoUri}
              onCheckPassed={(sample) => {
                setActiveSample(sample);
                navigateTo('RESULTS');
              }}
              onRetake={() => navigateTo('CAPTURE')}
            />
          )}

          {currentScreen === 'RESULTS' && activeInspection && activeSample && (
            <ResultsScreen
              inspection={activeInspection}
              sample={activeSample}
              videoResult={activeVideoResult}
              onFinalize={(finalized) => {
                setActiveInspection(finalized);
                navigateTo('FINAL_REPORT');
              }}
              onAddSample={() => navigateTo('CAPTURE')}
            />
          )}

          {currentScreen === 'FINAL_REPORT' && activeInspection && (
            <FinalReportScreen
              inspection={activeInspection}
              onStartNewInspection={() => {
                setActiveInspection(null);
                setActiveSample(null);
                setCapturedPhotoUri(null);
                navigateTo('HOME');
              }}
            />
          )}
        </Animated.View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#09090b', // Deep sleek backdrop on desktop web
  },
  safeAreaCapture: {
    backgroundColor: '#000000',
  },
  appShell: {
    flex: 1,
    width: '100%',
    maxWidth: 520,
    alignSelf: 'center',
    backgroundColor: Colors.bg,
    ...(Platform.OS === 'web'
      ? {
          borderLeftWidth: 1,
          borderRightWidth: 1,
          borderColor: 'rgba(255, 255, 255, 0.08)',
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 12 },
          shadowOpacity: 0.35,
          shadowRadius: 28,
        }
      : {}),
  },
  appShellCapture: {
    maxWidth: '100%',
    backgroundColor: '#000000',
    borderLeftWidth: 0,
    borderRightWidth: 0,
  },
  content: {
    flex: 1,
  },
});

