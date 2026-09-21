import { Platform } from 'react-native';
import * as ExpoHaptics from 'expo-haptics';

/**
 * Cepa Mandi Haptic Feedback Engine
 * Provides subtle tactile cues for procurement officers in the field.
 * Safely falls back on web or devices lacking haptic motors.
 */
export const Haptics = {
  /**
   * Light selection tick (used for segmented controls, toggle switches, filter chips).
   */
  selection: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.selectionAsync();
      }
    } catch {
      // Graceful fallback on unsupported hardware
    }
  },

  /**
   * Subtle tap feedback (buttons, cards, pressable icons).
   */
  light: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Light);
      }
    } catch {
      // Graceful fallback
    }
  },

  /**
   * Definite medium impact (photo shutter, sample card press, manual override toggle).
   */
  medium: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Medium);
      }
    } catch {
      // Graceful fallback
    }
  },

  /**
   * Heavy firm impact (inspection submission, lot finalization, calibration board lock).
   */
  heavy: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Heavy);
      }
    } catch {
      // Graceful fallback
    }
  },

  /**
   * Notification success chime (all quality gates passed, PDF certificate ready).
   */
  success: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.notificationAsync(ExpoHaptics.NotificationFeedbackType.Success);
      }
    } catch {
      // Graceful fallback
    }
  },

  /**
   * Warning vibration (URS classification warning, borderline blur / glare flag).
   */
  warning: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.notificationAsync(ExpoHaptics.NotificationFeedbackType.Warning);
      }
    } catch {
      // Graceful fallback
    }
  },

  /**
   * Error buzz (quality gate failed, camera capture error, network timeout).
   */
  error: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.notificationAsync(ExpoHaptics.NotificationFeedbackType.Error);
      }
    } catch {
      // Graceful fallback
    }
  },

  /**
   * Double-tap snap sequence (scale bar calibrated, ChArUco 4-corners locked).
   */
  snap: async () => {
    try {
      if (Platform.OS !== 'web') {
        await ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Medium);
        setTimeout(async () => {
          try {
            await ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Light);
          } catch {}
        }, 80);
      }
    } catch {
      // Graceful fallback
    }
  },
};
