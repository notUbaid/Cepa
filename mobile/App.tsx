import React, { useEffect, useState } from 'react';
import { SafeAreaView, StatusBar, StyleSheet, View } from 'react-native';
import { ApiClient } from './src/api/client';
import { Header } from './src/components/Header';
import { CaptureScreen } from './src/screens/CaptureScreen';
import { FinalReportScreen } from './src/screens/FinalReportScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { NewInspectionScreen } from './src/screens/NewInspectionScreen';
import { QualityCheckScreen } from './src/screens/QualityCheckScreen';
import { ResultsScreen } from './src/screens/ResultsScreen';
import { InspectionDetail, SampleDetail } from './src/types';

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
  const [policyVersion, setPolicyVersion] = useState('DEMO_ASSUMPTION_v1');
  const [isMockActive, setIsMockActive] = useState(true);

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
        setCurrentScreen('FINAL_REPORT');
      } else if (inspection.sample_ids.length > 0) {
        // Load the latest sample
        const latestSampleId = inspection.sample_ids[inspection.sample_ids.length - 1];
        const sample = await ApiClient.getSample(inspection.id, latestSampleId);
        setActiveSample(sample);
        setCurrentScreen('RESULTS');
      } else {
        setCurrentScreen('CAPTURE');
      }
    } catch (e: any) {
      alert(`Could not load inspection: ${e.message}`);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor="#1b263b" />
      <Header
        serverConnected={serverOnline}
        policyVersion={policyVersion}
        isMockActive={isMockActive}
      />

      <View style={styles.content}>
        {currentScreen === 'HOME' && (
          <HomeScreen
            onStartNewInspection={() => setCurrentScreen('NEW_INSPECTION')}
            onSelectInspection={handleSelectInspection}
          />
        )}

        {currentScreen === 'NEW_INSPECTION' && (
          <NewInspectionScreen
            onInspectionCreated={(inspection) => {
              setActiveInspection(inspection);
              setCurrentScreen('CAPTURE');
            }}
            onCancel={() => setCurrentScreen('HOME')}
          />
        )}

        {currentScreen === 'CAPTURE' && activeInspection && (
          <CaptureScreen
            inspection={activeInspection}
            onPhotoCaptured={(uri) => {
              setCapturedPhotoUri(uri);
              setCurrentScreen('QUALITY_CHECK');
            }}
            onCancel={() => setCurrentScreen('HOME')}
          />
        )}

        {currentScreen === 'QUALITY_CHECK' && activeInspection && capturedPhotoUri && (
          <QualityCheckScreen
            inspection={activeInspection}
            photoUri={capturedPhotoUri}
            onCheckPassed={(sample) => {
              setActiveSample(sample);
              setCurrentScreen('RESULTS');
            }}
            onRetake={() => setCurrentScreen('CAPTURE')}
          />
        )}

        {currentScreen === 'RESULTS' && activeInspection && activeSample && (
          <ResultsScreen
            inspection={activeInspection}
            sample={activeSample}
            onFinalize={(finalized) => {
              setActiveInspection(finalized);
              setCurrentScreen('FINAL_REPORT');
            }}
            onAddSample={() => setCurrentScreen('CAPTURE')}
          />
        )}

        {currentScreen === 'FINAL_REPORT' && activeInspection && (
          <FinalReportScreen
            inspection={activeInspection}
            onStartNewInspection={() => {
              setActiveInspection(null);
              setActiveSample(null);
              setCapturedPhotoUri(null);
              setCurrentScreen('HOME');
            }}
          />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0d1b2a',
  },
  content: {
    flex: 1,
  },
});
