import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import * as Location from 'expo-location';
import { Feather } from '@expo/vector-icons';
import { ApiClient } from '../api/client';
import { InspectionDetail } from '../types';
import {
  AnimatedPressable,
  Colors,
  FadeInView,
  Haptics,
  RadarPulse,
  Radius,
  Shadows,
  Spacing,
  Typography,
} from '../ui';

interface NewInspectionScreenProps {
  onInspectionCreated: (inspection: InspectionDetail, mode?: 'CAMERA' | 'UPLOAD' | 'VIDEO') => void;
  onCancel: () => void;
  initialMode?: 'CAMERA' | 'UPLOAD' | 'VIDEO';
}

export const NewInspectionScreen: React.FC<NewInspectionScreenProps> = ({
  onInspectionCreated,
  onCancel,
  initialMode = 'CAMERA',
}) => {
  const [lotId, setLotId] = useState('');
  const [farmerName, setFarmerName] = useState('');
  const [farmerId, setFarmerId] = useState('');
  const [procurementCentre, setProcurementCentre] = useState('');
  const [officerName, setOfficerName] = useState('');
  const [officerId, setOfficerId] = useState('');
  const [notes, setNotes] = useState('');
  const [cutTestPerformed, setCutTestPerformed] = useState(false);
  const [cutTestBulbsCount, setCutTestBulbsCount] = useState('10');
  const [cutTestInternalDefects, setCutTestInternalDefects] = useState('0');
  const [cutTestNotes, setCutTestNotes] = useState('');

  // GPS state
  const [location, setLocation] = useState<{
    lat?: number;
    lon?: number;
    accuracy?: number;
    status: 'fetching' | 'locked' | 'denied' | 'unavailable';
  }>({ status: 'fetching' });

  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          setLocation({ status: 'denied' });
          return;
        }
        const pos = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        setLocation({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy ?? undefined,
          status: 'locked',
        });
      } catch (err) {
        console.warn('Location retrieval error', err);
        setLocation({ status: 'unavailable' });
      }
    })();
  }, []);

  const handleStartCapture = async (targetMode: 'CAMERA' | 'UPLOAD' | 'VIDEO' = initialMode) => {
    Haptics.heavy();
    setSubmitting(true);
    try {
      const inspection = await ApiClient.createInspection({
        lot_id: lotId.trim() || undefined,
        farmer_name: farmerName.trim() || undefined,
        farmer_id: farmerId.trim() || undefined,
        procurement_centre: procurementCentre.trim() || undefined,
        officer_name: officerName.trim() || undefined,
        officer_id: officerId.trim() || undefined,
        notes: notes.trim() || undefined,
        geo_lat: location.lat,
        geo_lon: location.lon,
        location_accuracy: location.accuracy,
        cut_test_performed: cutTestPerformed,
        cut_test_bulbs_count: cutTestPerformed ? parseInt(cutTestBulbsCount, 10) || 0 : undefined,
        cut_test_internal_defects_found: cutTestPerformed ? parseInt(cutTestInternalDefects, 10) || 0 : undefined,
        cut_test_notes: cutTestPerformed ? (cutTestNotes.trim() || undefined) : undefined,
      });
      onInspectionCreated(inspection, targetMode);
    } catch (err: any) {
      console.warn('Network inspection creation failed, falling back to local inspection:', err.message);
      // Resilient local inspection object so user is NEVER blocked from opening the camera
      const fallbackInspection: InspectionDetail = {
        id: `insp-offline-${Date.now()}`,
        lot_id: lotId.trim() || `LOT-${Date.now().toString().slice(-4)}`,
        created_at: new Date().toISOString(),
        finalized_at: null,
        sample_count: 0,
        status: 'DRAFT',
        procurement_centre: procurementCentre.trim() || 'Field Mandi',
        officer_name: officerName.trim() || 'Officer',
        officer_id: officerId.trim() || 'OFF-01',
        notes: notes.trim() || null,
        cut_test_performed: cutTestPerformed,
        cut_test_bulbs_count: cutTestPerformed ? parseInt(cutTestBulbsCount, 10) || 0 : undefined,
        cut_test_internal_defects_found: cutTestPerformed ? parseInt(cutTestInternalDefects, 10) || 0 : undefined,
        cut_test_notes: cutTestPerformed ? (cutTestNotes.trim() || null) : null,
        geo_lat: location.lat ?? null,
        geo_lon: location.lon ?? null,
        location_accuracy: location.accuracy ?? null,
        location_note: null,
        updated_at: new Date().toISOString(),
        total_bulbs: 0,
        grade_a_count: 0,
        urs_count: 0,
        rejected_count: 0,
        review_count: 0,
        grade_a_pct: 0,
        urs_pct: 0,
        rejected_pct: 0,
        sample_ids: [],
        has_report: false,
        report_id: null,
      };
      onInspectionCreated(fallbackInspection, targetMode);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Step Header */}
        <FadeInView delay={50} distance={12}>
          <View style={styles.titleRow}>
            <Text style={styles.screenTitle}>Lot Details</Text>
            <Text style={styles.stepSubtitle}>
              Step 1 of 3 • Consignment identification and APMC Mandi geolocation.
            </Text>
          </View>
        </FadeInView>

        {/* GPS Radar Card */}
        <FadeInView delay={100} distance={12}>
          <View style={styles.gpsCard}>
            <View style={styles.gpsHeader}>
              <View style={styles.radarContainer}>
                <RadarPulse
                  size={26}
                  color={
                    location.status === 'locked'
                      ? Colors.accent
                      : location.status === 'fetching'
                      ? Colors.textSecondary
                      : Colors.urs
                  }
                  active={location.status === 'fetching'}
                />
              </View>
              <View style={styles.gpsInfo}>
                <Text style={styles.gpsTitle}>Device-Reported Location</Text>
                {location.status === 'fetching' ? (
                  <Text style={styles.gpsText}>Acquiring device GNSS location...</Text>
                ) : location.status === 'locked' ? (
                  <Text style={styles.gpsLockedText}>
                    Device GNSS: {location.lat?.toFixed(4)}° N, {location.lon?.toFixed(4)}° E (±{location.accuracy?.toFixed(0)} m)
                  </Text>
                ) : (
                  <Text style={styles.gpsDeniedText}>
                    Location Unavailable ({location.status})
                  </Text>
                )}
              </View>
            </View>
          </View>
        </FadeInView>

        {/* Form Inputs Card */}
        <FadeInView delay={160} distance={15}>
          <View style={styles.formCard}>
            <View style={styles.quickPresetRow}>
              <Text style={styles.quickPresetLabel}>Quick Fill:</Text>
              <AnimatedPressable
                haptic="selection"
                onPress={() => {
                  setLotId(`LOT-${new Date().getFullYear()}-NSK-${Math.floor(100 + Math.random() * 900)}`);
                  setProcurementCentre('Lasalgaon APMC Mandi, Nashik');
                  setOfficerName('S. Patil');
                  setOfficerId('NAFED-MH-084');
                  setNotes('Rabi Season · Garwa Red Onion · FAQ Grade Assessment');
                }}
                style={styles.quickPresetChip}
              >
                <Text style={styles.quickPresetChipText}>+ Lasalgaon Mandi FAQ</Text>
              </AnimatedPressable>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Lot Identifier</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. LOT-2026-NASHIK-409"
                placeholderTextColor={Colors.textDim}
                value={lotId}
                onChangeText={setLotId}
              />
            </View>

            <View style={styles.rowFields}>
              <View style={[styles.fieldGroup, { flex: 1, marginRight: Spacing.sm }]}>
                <Text style={styles.label}>Farmer Name (किसान का नाम)</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g. Ramesh Patil"
                  placeholderTextColor={Colors.textDim}
                  value={farmerName}
                  onChangeText={setFarmerName}
                />
              </View>
              <View style={[styles.fieldGroup, { flex: 1 }]}>
                <Text style={styles.label}>AgriStack Farmer ID</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g. MH-NSK-2026-8910"
                  placeholderTextColor={Colors.textDim}
                  value={farmerId}
                  onChangeText={setFarmerId}
                />
              </View>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>APMC Mandi Yard</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. Lasalgaon APMC Mandi, Nashik"
                placeholderTextColor={Colors.textDim}
                value={procurementCentre}
                onChangeText={setProcurementCentre}
              />
            </View>

            <View style={styles.rowFields}>
              <View style={[styles.fieldGroup, { flex: 1, marginRight: Spacing.sm }]}>
                <Text style={styles.label}>Officer Name</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g. Rajesh Sharma"
                  placeholderTextColor={Colors.textDim}
                  value={officerName}
                  onChangeText={setOfficerName}
                />
              </View>
              <View style={[styles.fieldGroup, { flex: 1 }]}>
                <Text style={styles.label}>Officer ID / Badge</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g. NAFED-4821"
                  placeholderTextColor={Colors.textDim}
                  value={officerId}
                  onChangeText={setOfficerId}
                />
              </View>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.label}>Consignment Notes</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                placeholder="Farmer name, variety (e.g. Nashik Red Rabi), lot tonnage, or comments."
                placeholderTextColor={Colors.textDim}
                multiline={true}
                numberOfLines={3}
                value={notes}
                onChangeText={setNotes}
              />
            </View>

            {/* Assayer Internal Cut-Test Protocol */}
            <View style={styles.cutTestCard}>
              <View style={styles.cutTestCardHeader}>
                <View style={{ flex: 1, paddingRight: Spacing.xs }}>
                  <Text style={styles.cutTestCardTag}>ASSAYER INTERNAL AUDIT · प्रत्यक्ष तपासणी</Text>
                  <Text style={styles.cutTestCardTitle}>Officer Destructive Cut-Test</Text>
                </View>
                <AnimatedPressable
                  haptic="selection"
                  style={[
                    styles.cutTestToggleBtn,
                    cutTestPerformed ? styles.cutTestToggleBtnActive : styles.cutTestToggleBtnInactive,
                  ]}
                  onPress={() => setCutTestPerformed(!cutTestPerformed)}
                >
                  <Feather
                    name={cutTestPerformed ? "check-circle" : "circle"}
                    size={12}
                    color={cutTestPerformed ? "#059669" : Colors.textMuted}
                  />
                  <Text
                    style={[
                      styles.cutTestToggleText,
                      cutTestPerformed ? styles.cutTestToggleTextActive : styles.cutTestToggleTextInactive,
                    ]}
                  >
                    {cutTestPerformed ? 'Performed' : 'Optical Only'}
                  </Text>
                </AnimatedPressable>
              </View>

              {cutTestPerformed ? (
                <View style={styles.cutTestExpandedContent}>
                  <Text style={styles.cutTestHelperText}>
                    Record results of cross-section slicing (sample 5–10 bulbs) to verify internal rot, smudged scales, or hollow heart before certifying.
                  </Text>
                  <View style={styles.rowFields}>
                    <View style={[styles.fieldGroup, { flex: 1, marginRight: Spacing.sm }]}>
                      <Text style={styles.label}>Bulbs Sliced</Text>
                      <TextInput
                        style={styles.input}
                        placeholder="10"
                        placeholderTextColor={Colors.textDim}
                        keyboardType="numeric"
                        value={cutTestBulbsCount}
                        onChangeText={setCutTestBulbsCount}
                      />
                    </View>
                    <View style={[styles.fieldGroup, { flex: 1 }]}>
                      <Text style={styles.label}>Internal Defects</Text>
                      <TextInput
                        style={styles.input}
                        placeholder="0"
                        placeholderTextColor={Colors.textDim}
                        keyboardType="numeric"
                        value={cutTestInternalDefects}
                        onChangeText={setCutTestInternalDefects}
                      />
                    </View>
                  </View>
                  <View style={styles.fieldGroup}>
                    <Text style={styles.label}>Internal Quality Notes</Text>
                    <TextInput
                      style={[styles.input, { minHeight: 46 }]}
                      placeholder="e.g. Sound dry scales, no internal rot or black mould"
                      placeholderTextColor={Colors.textDim}
                      value={cutTestNotes}
                      onChangeText={setCutTestNotes}
                    />
                  </View>
                </View>
              ) : (
                <Text style={styles.cutTestOptText}>
                  Default: Non-destructive optical grading active. Tap toggle if physical cross-section slicing was conducted.
                </Text>
              )}
            </View>
          </View>
        </FadeInView>

        {/* Action Buttons */}
        <FadeInView delay={220} distance={15}>
          <View style={styles.actionsContainer}>
            <View style={styles.btnRow}>
              <AnimatedPressable
                haptic="light"
                style={styles.cancelBtn}
                onPress={onCancel}
                disabled={submitting}
              >
                <Text style={styles.cancelBtnText}>Back</Text>
              </AnimatedPressable>

              <AnimatedPressable
                haptic="heavy"
                style={styles.submitBtn}
                onPress={() => handleStartCapture(initialMode)}
                disabled={submitting}
              >
                {submitting ? (
                  <ActivityIndicator color="#ffffff" size="small" />
                ) : (
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <Text style={styles.submitBtnText}>
                      {initialMode === 'VIDEO'
                        ? 'Continue to Video Sweep'
                        : initialMode === 'UPLOAD'
                        ? 'Continue to Photo Upload'
                        : 'Continue to Camera'}
                    </Text>
                    <Feather
                      name={initialMode === 'VIDEO' ? 'video' : initialMode === 'UPLOAD' ? 'upload-cloud' : 'arrow-right'}
                      size={14}
                      color="#ffffff"
                    />
                  </View>
                )}
              </AnimatedPressable>
            </View>

            {/* Alternative quick triggers */}
            <View style={styles.altButtonsRow}>
              {initialMode !== 'CAMERA' && (
                <AnimatedPressable
                  haptic="medium"
                  style={[styles.altBtn, { flex: 1 }]}
                  onPress={() => handleStartCapture('CAMERA')}
                  disabled={submitting}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <Feather name="camera" size={13} color="#059669" />
                    <Text style={styles.altBtnText}>Live Camera</Text>
                  </View>
                </AnimatedPressable>
              )}

              {initialMode !== 'VIDEO' && (
                <AnimatedPressable
                  haptic="medium"
                  style={[styles.altBtn, { flex: 1 }]}
                  onPress={() => handleStartCapture('VIDEO')}
                  disabled={submitting}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <Feather name="video" size={13} color="#059669" />
                    <Text style={styles.altBtnText}>Video Sorter</Text>
                  </View>
                </AnimatedPressable>
              )}

              {initialMode !== 'UPLOAD' && (
                <AnimatedPressable
                  haptic="medium"
                  style={[styles.altBtn, { flex: 1 }]}
                  onPress={() => handleStartCapture('UPLOAD')}
                  disabled={submitting}
                >
                  <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <Feather name="upload-cloud" size={13} color="#059669" />
                    <Text style={styles.altBtnText}>Upload File</Text>
                  </View>
                </AnimatedPressable>
              )}
            </View>
          </View>
        </FadeInView>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  scrollContent: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.hero,
  },
  titleRow: {
    marginBottom: Spacing.md,
  },
  stepBadge: {
    alignSelf: 'flex-start',
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.xs,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 6,
  },
  stepBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textSecondary,
    letterSpacing: 0.3,
  },
  screenTitle: {
    ...Typography.title1,
    color: Colors.text,
  },
  stepSubtitle: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: 4,
    lineHeight: 18,
  },
  gpsCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.md,
    marginBottom: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.card,
  },
  gpsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  radarContainer: {
    width: 34,
    height: 34,
    justifyContent: 'center',
    alignItems: 'center',
  },
  gpsInfo: {
    flex: 1,
  },
  gpsTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.textSecondary,
  },
  gpsText: {
    fontSize: 12,
    color: Colors.textMuted,
    marginTop: 2,
  },
  gpsLockedText: {
    fontSize: 11,
    color: Colors.textSecondary,
    fontWeight: '600',
    marginTop: 2,
  },
  gpsDeniedText: {
    fontSize: 11,
    color: Colors.urs,
    marginTop: 2,
  },
  formCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    gap: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadows.card,
  },
  quickPresetRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  quickPresetLabel: {
    fontSize: 11,
    color: Colors.textDim,
  },
  quickPresetChip: {
    backgroundColor: Colors.cardBgElevated,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  quickPresetChipText: {
    fontSize: 11,
    fontWeight: '600',
    color: Colors.accentTeal,
  },
  fieldGroup: {
    gap: 5,
  },
  rowFields: {
    flexDirection: 'row',
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.text,
  },
  input: {
    backgroundColor: Colors.cardBgElevated,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    color: Colors.text,
    fontSize: 13,
  },
  textArea: {
    minHeight: 74,
    textAlignVertical: 'top',
  },
  actionsContainer: {
    marginTop: Spacing.xl,
    gap: Spacing.sm,
  },
  btnRow: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 13,
    borderRadius: Radius.md,
    backgroundColor: Colors.cardBg,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  cancelBtnText: {
    color: Colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  submitBtn: {
    flex: 2.2,
    paddingVertical: 13,
    borderRadius: Radius.md,
    backgroundColor: Colors.accent,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.accent,
    ...Shadows.card,
  },
  submitBtnText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  uploadDirectBtn: {
    paddingVertical: 13,
    borderRadius: Radius.md,
    backgroundColor: Colors.cardBgElevated,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  uploadDirectBtnText: {
    color: Colors.text,
    fontSize: 13,
    fontWeight: '600',
  },
  altButtonsRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    marginTop: Spacing.xs,
  },
  altBtn: {
    paddingVertical: 12,
    borderRadius: Radius.md,
    backgroundColor: Colors.cardBgElevated,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  altBtnText: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  cutTestCard: {
    backgroundColor: Colors.cardBgElevated,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: Colors.borderMuted,
    padding: Spacing.md,
    marginTop: Spacing.sm,
  },
  cutTestCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cutTestCardTag: {
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: '700',
    color: Colors.accentTeal,
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  cutTestCardTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.text,
  },
  cutTestToggleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: Radius.xs,
    borderWidth: 1,
  },
  cutTestToggleBtnActive: {
    backgroundColor: '#ecfdf5',
    borderColor: '#a7f3d0',
  },
  cutTestToggleBtnInactive: {
    backgroundColor: Colors.cardBg,
    borderColor: Colors.borderMuted,
  },
  cutTestToggleText: {
    fontSize: 10,
    fontWeight: '700',
    fontFamily: 'monospace',
  },
  cutTestToggleTextActive: {
    color: '#059669',
  },
  cutTestToggleTextInactive: {
    color: Colors.textMuted,
  },
  cutTestExpandedContent: {
    marginTop: Spacing.sm,
    paddingTop: Spacing.xs,
    borderTopWidth: 1,
    borderTopColor: Colors.borderMuted,
  },
  cutTestHelperText: {
    fontSize: 11,
    color: Colors.textMuted,
    lineHeight: 16,
    marginBottom: Spacing.sm,
  },
  cutTestOptText: {
    fontSize: 11,
    color: Colors.textDim,
    lineHeight: 16,
    marginTop: 6,
  },
});
