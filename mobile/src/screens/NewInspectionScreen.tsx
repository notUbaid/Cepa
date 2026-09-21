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
  onInspectionCreated: (inspection: InspectionDetail) => void;
  onCancel: () => void;
}

export const NewInspectionScreen: React.FC<NewInspectionScreenProps> = ({
  onInspectionCreated,
  onCancel,
}) => {
  const [lotId, setLotId] = useState('');
  const [procurementCentre, setProcurementCentre] = useState('');
  const [officerName, setOfficerName] = useState('');
  const [officerId, setOfficerId] = useState('');
  const [notes, setNotes] = useState('');

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

  const handleStartCapture = async () => {
    Haptics.heavy();
    setSubmitting(true);
    try {
      const inspection = await ApiClient.createInspection({
        lot_id: lotId.trim() || undefined,
        procurement_centre: procurementCentre.trim() || undefined,
        officer_name: officerName.trim() || undefined,
        officer_id: officerId.trim() || undefined,
        notes: notes.trim() || undefined,
        geo_lat: location.lat,
        geo_lon: location.lon,
        location_accuracy: location.accuracy,
      });
      onInspectionCreated(inspection);
    } catch (err: any) {
      Haptics.error();
      alert(`Could not create inspection: ${err.message}`);
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
                <Text style={styles.gpsTitle}>Mandi Geolocation</Text>
                {location.status === 'fetching' ? (
                  <Text style={styles.gpsText}>Acquiring GPS location...</Text>
                ) : location.status === 'locked' ? (
                  <Text style={styles.gpsLockedText}>
                    GPS Locked: {location.lat?.toFixed(4)}° N, {location.lon?.toFixed(4)}° E (±{location.accuracy?.toFixed(0)} m)
                  </Text>
                ) : (
                  <Text style={styles.gpsDeniedText}>
                    GPS Offline ({location.status})
                  </Text>
                )}
              </View>
            </View>
          </View>
        </FadeInView>

        {/* Form Inputs Card */}
        <FadeInView delay={160} distance={15}>
          <View style={styles.formCard}>
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
          </View>
        </FadeInView>

        {/* Action Buttons */}
        <FadeInView delay={220} distance={15}>
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
              onPress={handleStartCapture}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <Text style={styles.submitBtnText}>Continue to Camera →</Text>
              )}
            </AnimatedPressable>
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
  btnRow: {
    flexDirection: 'row',
    marginTop: Spacing.xl,
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
});
