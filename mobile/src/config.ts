import { Platform } from 'react-native';

const PRODUCTION_BACKEND_URL = 'https://cepa-backend.onrender.com';

function resolveDefaultApiBaseUrl(): string {
  // 1. If running in browser on a remote domain (e.g. Vercel) or over HTTPS,
  // we MUST use the production HTTPS backend. Calling http://localhost from an HTTPS site
  // is blocked by browser Mixed Content security rules and is unreachable on phones.
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    const protocol = window.location.protocol;
    if ((host && host !== 'localhost' && host !== '127.0.0.1') || protocol === 'https:') {
      return PRODUCTION_BACKEND_URL;
    }
  }

  // 2. User override from localStorage if set (local dev only)
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const saved = window.localStorage.getItem('cepa_api_base_url');
      if (saved && saved.trim() && !saved.includes('localhost:8000')) {
        return saved.trim().replace(/\/+$/, '');
      }
    } catch {
      // localStorage may be disabled in restricted iframe/browser modes
    }
  }

  // 3. Environment variable (only if not an insecure localhost URL on a remote host)
  const configuredUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, '');
  }

  // 4. Default local development backend
  return Platform.select({
    android: 'http://10.0.2.2:8001',
    default: 'http://localhost:8001',
  })!;
}

export const DEFAULT_API_BASE_URL = resolveDefaultApiBaseUrl();

let currentBaseUrl = DEFAULT_API_BASE_URL;

export const getApiBaseUrl = () => {
  // Runtime guard: if page is on HTTPS or non-localhost, never allow an insecure http://localhost URL
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    const protocol = window.location.protocol;
    if ((host && host !== 'localhost' && host !== '127.0.0.1') || protocol === 'https:') {
      if (currentBaseUrl.includes('localhost') || currentBaseUrl.includes('127.0.0.1') || currentBaseUrl.startsWith('http:')) {
        currentBaseUrl = PRODUCTION_BACKEND_URL;
      }
    }
  }
  return currentBaseUrl;
};

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

