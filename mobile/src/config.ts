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
      return 'http://localhost:8000';
    }
  }

  // 3. User override from localStorage if set (local dev only)
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const saved = window.localStorage.getItem('cepa_api_base_url');
      if (saved && saved.trim()) {
        return saved.trim().replace(/\/+$/, '');
      }
    } catch {}
  }

  // 4. Default for native devices (Expo Go / standalone APK on Android & iOS)
  // Always use the robust cloud backend so physical phones connect seamlessly without loopback failures
  return PRODUCTION_BACKEND_URL;
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

export const DEFAULT_OFFICER_TOKEN =
  process.env.EXPO_PUBLIC_OFFICER_TOKEN || 'cepa-officer-secret-key-2026';

let currentOfficerToken = DEFAULT_OFFICER_TOKEN;
export const getOfficerToken = () => currentOfficerToken;
export const setOfficerToken = (token: string) => {
  currentOfficerToken = token;
};

/**
 * Resolves any backend media or API URL against the currently active API base URL.
 * Handles:
 * - Hardcoded localhost:8000 or 127.0.0.1:8000 URLs returned by backend -> rewrites to currentBaseUrl
 * - Relative paths (e.g. /api/v1/storage/... or crops/...) -> prepends currentBaseUrl
 * - Data URIs (base64) -> returned unchanged
 * - Remote HTTPS URLs (Render/S3) -> returned unchanged
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  const trimmed = url.trim();
  if (!trimmed) return null;

  // Base64 data URIs are self-contained
  if (trimmed.startsWith('data:')) return trimmed;

  const baseUrl = getApiBaseUrl().replace(/\/+$/, '');

  // Rewrite hardcoded localhost:8000 or 127.0.0.1:8000 to the device-reachable base URL
  const rewritten = trimmed.replace(
    /^https?:\/\/(localhost|127\.0\.0\.1):8000(?=\/|$)/i,
    baseUrl
  );

  // If path is relative with leading slash
  if (rewritten.startsWith('/')) {
    return `${baseUrl}${rewritten}`;
  }

  // If path is relative storage path without leading slash
  if (
    rewritten.startsWith('api/') ||
    rewritten.startsWith('crops/') ||
    rewritten.startsWith('masks/') ||
    rewritten.startsWith('images/') ||
    rewritten.startsWith('reports/')
  ) {
    return `${baseUrl}/${rewritten}`;
  }

  return rewritten;
}
