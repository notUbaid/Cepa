import { Platform } from 'react-native';

export const PRODUCTION_BACKEND_URL = 'https://cepa-backend.onrender.com';

function isHostedEnvironment(): boolean {
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    const protocol = window.location.protocol;
    // Any HTTPS connection or non-localhost domain is production/hosted
    if (protocol === 'https:' || (host && host !== 'localhost' && host !== '127.0.0.1')) {
      return true;
    }
  }
  return false;
}

function resolveDefaultApiBaseUrl(): string {
  // 1. If on hosted domain (Vercel, Render, or HTTPS), strictly enforce production backend
  if (isHostedEnvironment()) {
    // Purge any stale localhost URLs saved in browser localStorage from earlier sessions
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const saved = window.localStorage.getItem('cepa_api_base_url');
        if (saved && (saved.includes('localhost') || saved.includes('127.0.0.1') || saved.startsWith('http:'))) {
          window.localStorage.removeItem('cepa_api_base_url');
        }
      } catch {}
    }
    return PRODUCTION_BACKEND_URL;
  }

  // 2. Localhost web development
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:8001';
    }
  }

  // 3. User override from localStorage if set (local dev only)
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const saved = window.localStorage.getItem('cepa_api_base_url');
      if (saved && saved.trim() && !saved.includes('localhost:8000')) {
        return saved.trim().replace(/\/+$/, '');
      }
    } catch {}
  }

  // 4. Fallback for native devices
  return Platform.select({
    android: 'http://10.0.2.2:8001',
    default: PRODUCTION_BACKEND_URL,
  })!;
}

export const DEFAULT_API_BASE_URL = resolveDefaultApiBaseUrl();

let currentBaseUrl = DEFAULT_API_BASE_URL;

export const getApiBaseUrl = (): string => {
  // Strict runtime guard: hosted/HTTPS browser MUST NEVER call http://localhost
  if (isHostedEnvironment()) {
    return PRODUCTION_BACKEND_URL;
  }
  return currentBaseUrl;
};

export const setApiBaseUrl = (url: string) => {
  currentBaseUrl = url.replace(/\/+$/, '');
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem('cepa_api_base_url', currentBaseUrl);
    } catch {}
  }
};
