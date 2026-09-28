import { Platform } from 'react-native';

// In Android Emulator, 10.0.2.2 points to host machine localhost.
// In iOS Simulator or Web, localhost points to host machine.
// For physical devices on Wi-Fi, change this to your computer's LAN IP (e.g. http://192.168.1.50:8000).
const configuredUrl = process.env.EXPO_PUBLIC_API_URL?.trim();

export const DEFAULT_API_BASE_URL = configuredUrl || Platform.select({
  android: 'http://10.0.2.2:8000',
  default: 'http://localhost:8000',
})!;

let currentBaseUrl = DEFAULT_API_BASE_URL;

export const getApiBaseUrl = () => currentBaseUrl;

export const setApiBaseUrl = (url: string) => {
  currentBaseUrl = url.replace(/\/+$/, '');
};
