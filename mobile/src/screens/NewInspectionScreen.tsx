import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Location from 'expo-location';
import { ApiClient } from '../api/client';
import { InspectionDetail } from '../types';

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
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.titleRow}>
          <Text style={styles.screenTitle}>New Lot Inspection</Text>
          <Text style={styles.stepIndicator}>Step 1 of 3: Lot Information</Text>
        </View>

        {/* GPS Status Box */}
        <View style={styles.gpsCard}>
          <Text style={styles.gpsTitle}>🛰️ GEOLOCATION VERIFICATION</Text>
          {location.status === 'fetching' ? (
            <View style={styles.gpsRow}>
              <ActivityIndicator size="small" color="#38bdf8" />
              <Text style={styles.gpsText}>Acquiring GPS coordinates...</Text>
            </View>
          ) : location.status === 'locked' ? (
            <Text style={styles.gpsLockedText}>
              ✓ GPS Locked: {location.lat?.toFixed(5)}°N, {location.lon?.toFixed(5)}°E (±
              {location.accuracy?.toFixed(0)}m)
            </Text>
          ) : (
            <Text style={styles.gpsDeniedText}>
              ⚠️ Location unavailable ({location.status}). Honest null will be recorded.
            </Text>
          )}
        </View>

        {/* Form Inputs */}
        <View style={styles.formCard}>
          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Lot Identifier / Batch Number</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. LOT-2026-NASHIK-409"
              placeholderTextColor="#64748b"
              value={lotId}
              onChangeText={setLotId}
            />
          </View>

          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Procurement Centre / Mandi Location</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. Lasalgaon APMC Mandi, Nashik"
              placeholderTextColor="#64748b"
              value={procurementCentre}
              onChangeText={setProcurementCentre}
            />
          </View>

          <View style={styles.rowFields}>
            <View style={[styles.fieldGroup, { flex: 1, marginRight: 8 }]}>
              <Text style={styles.label}>Officer Name</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. Rajesh Sharma"
                placeholderTextColor="#64748b"
                value={officerName}
                onChangeText={setOfficerName}
              />
            </View>
            <View style={[styles.fieldGroup, { flex: 1 }]}>
              <Text style={styles.label}>Officer ID</Text>
              <TextInput
                style={styles.input}
                placeholder="e.g. NAFED-4821"
                placeholderTextColor="#64748b"
                value={officerId}
                onChangeText={setOfficerId}
              />
            </View>
          </View>

          <View style={styles.fieldGroup}>
            <Text style={styles.label}>Consignment Remarks / Farmer Details</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              placeholder="e.g. Farmer: Ramdas Patil, Variety: Rabi Red, 50 bags sampled"
              placeholderTextColor="#64748b"
              multiline={true}
              numberOfLines={3}
              value={notes}
              onChangeText={setNotes}
            />
          </View>
        </View>

        {/* Buttons */}
        <View style={styles.btnRow}>
          <TouchableOpacity
            style={styles.cancelBtn}
            onPress={onCancel}
            disabled={submitting}
          >
            <Text style={styles.cancelBtnText}>Cancel</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.submitBtn}
            onPress={handleStartCapture}
            disabled={submitting}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Text style={styles.submitBtnText}>Proceed to Camera →</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1b2a',
  },
  scrollContent: {
    padding: 16,
  },
  titleRow: {
    marginBottom: 16,
  },
  screenTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#f8f9fa',
  },
  stepIndicator: {
    fontSize: 12,
    color: '#38bdf8',
    marginTop: 2,
    fontWeight: '600',
  },
  gpsCard: {
    backgroundColor: '#162232',
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#223348',
  },
  gpsTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: '#94a3b8',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  gpsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  gpsText: {
    fontSize: 11,
    color: '#94a3b8',
  },
  gpsLockedText: {
    fontSize: 11,
    color: '#2ecc71',
    fontWeight: '600',
  },
  gpsDeniedText: {
    fontSize: 11,
    color: '#e67e22',
  },
  formCard: {
    backgroundColor: '#1b263b',
    borderRadius: 12,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#2e3d52',
  },
  fieldGroup: {
    gap: 4,
  },
  rowFields: {
    flexDirection: 'row',
  },
  label: {
    fontSize: 12,
    fontWeight: '700',
    color: '#cbd5e1',
  },
  input: {
    backgroundColor: '#0d1b2a',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: '#f8f9fa',
    fontSize: 13,
  },
  textArea: {
    minHeight: 70,
    textAlignVertical: 'top',
  },
  btnRow: {
    flexDirection: 'row',
    marginTop: 20,
    gap: 12,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 8,
    backgroundColor: '#334155',
    alignItems: 'center',
  },
  cancelBtnText: {
    color: '#cbd5e1',
    fontSize: 13,
    fontWeight: '700',
  },
  submitBtn: {
    flex: 2,
    paddingVertical: 14,
    borderRadius: 8,
    backgroundColor: '#0284c7',
    alignItems: 'center',
  },
  submitBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '800',
  },
});
