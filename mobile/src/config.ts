import { Platform } from 'react-native';

const PRODUCTION_BACKEND_URL = 'https://cepa-backend.onrender.com';

function resolveDefaultApiBaseUrl(): string {
  const configuredUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const saved = window.localStorage.getItem('cepa_api_base_url');
      if (saved && saved.trim()) {
        return saved.trim().replace(/\/+$/, '');
      }
    } catch {
      // localStorage may be disabled in restricted iframe/browser modes
    }
  }

  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return PRODUCTION_BACKEND_URL;
    }
  }

  return Platform.select({
    android: 'http://10.0.2.2:8000',
    default: 'http://localhost:8000',
  })!;
}

export const DEFAULT_API_BASE_URL = resolveDefaultApiBaseUrl();

let currentBaseUrl = DEFAULT_API_BASE_URL;

export const getApiBaseUrl = () => currentBaseUrl;

export const setApiBaseUrl = (url: string) => {
  currentBaseUrl = url.replace(/\/+$/, '');
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('cepa_api_base_url', currentBaseUrl);
    } catch {
      // Ignore localStorage errors
    }
  }
};

