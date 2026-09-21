import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
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
import { InspectionDetail, SampleDetail } from './src/types';
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
  const [capturedPhotoUri, setCapturedPhotoUri] = useState<string | null>(null);

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
        navigateTo('CAPTURE');
      }
    } catch (e: any) {
      alert(`Could not load inspection: ${e.message}`);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={Colors.bg} />
      <Header
        serverConnected={serverOnline}
        policyVersion={policyVersion}
        isMockActive={isMockActive}
      />

      <Animated.View style={[styles.content, { opacity: screenFade }]}>
        {currentScreen === 'HOME' && (
          <HomeScreen
            onStartNewInspection={() => navigateTo('NEW_INSPECTION')}
            onSelectInspection={handleSelectInspection}
          />
        )}

        {currentScreen === 'NEW_INSPECTION' && (
          <NewInspectionScreen
            onInspectionCreated={(inspection) => {
              setActiveInspection(inspection);
              navigateTo('CAPTURE');
            }}
            onCancel={() => navigateTo('HOME')}
          />
        )}

        {currentScreen === 'CAPTURE' && activeInspection && (
          <CaptureScreen
            inspection={activeInspection}
            onPhotoCaptured={(uri) => {
              setCapturedPhotoUri(uri);
              navigateTo('QUALITY_CHECK');
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  content: {
    flex: 1,
  },
});
