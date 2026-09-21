/**
 * Cepa Mandi Design System — Core Design Tokens
 * Linear / Apple-grade dark palette engineered for high-contrast field operations.
 */

export const Colors = {
  // Surfaces
  bg: '#070d18',
  cardBg: '#0f172a',
  cardBgElevated: '#1e293b',
  cardBgHover: '#24334d',
  surfaceGlass: 'rgba(15, 23, 42, 0.88)',

  // Borders
  border: 'rgba(56, 189, 248, 0.18)',
  borderActive: 'rgba(56, 189, 248, 0.55)',
  borderMuted: 'rgba(255, 255, 255, 0.08)',
  borderHighlight: 'rgba(255, 255, 255, 0.15)',

  // Brand Accents
  accent: '#38bdf8',
  accentDark: '#0284c7',
  accentGlow: 'rgba(56, 189, 248, 0.35)',
  accentSubtle: 'rgba(56, 189, 248, 0.12)',

  // Grading Statuses
  gradeA: '#10b981',
  gradeABg: 'rgba(16, 185, 129, 0.12)',
  gradeAGlow: 'rgba(16, 185, 129, 0.3)',

  urs: '#f59e0b',
  ursBg: 'rgba(245, 158, 11, 0.12)',
  ursGlow: 'rgba(245, 158, 11, 0.3)',

  reject: '#ef4444',
  rejectBg: 'rgba(239, 68, 68, 0.12)',
  rejectGlow: 'rgba(239, 68, 68, 0.3)',

  review: '#8b5cf6',
  reviewBg: 'rgba(139, 92, 246, 0.12)',
  reviewGlow: 'rgba(139, 92, 246, 0.3)',

  // Typography
  text: '#f8fafc',
  textSecondary: '#cbd5e1',
  textMuted: '#94a3b8',
  textDim: '#64748b',

  // Skeleton & Overlays
  skeletonBase: '#152138',
  skeletonHighlight: '#223456',
  overlayDark: 'rgba(7, 13, 24, 0.82)',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  hero: 32,
};

export const Radius = {
  xs: 4,
  sm: 6,
  md: 10,
  lg: 14,
  xl: 18,
  pill: 9999,
};

export const Typography = {
  hero: {
    fontSize: 28,
    fontWeight: '700' as const,
    color: Colors.text,
    letterSpacing: -0.5,
  },
  title1: {
    fontSize: 20,
    fontWeight: '700' as const,
    color: Colors.text,
    letterSpacing: -0.3,
  },
  title2: {
    fontSize: 17,
    fontWeight: '600' as const,
    color: Colors.text,
    letterSpacing: -0.2,
  },
  body: {
    fontSize: 14,
    fontWeight: '400' as const,
    color: Colors.textSecondary,
    lineHeight: 20,
  },
  bodyMedium: {
    fontSize: 14,
    fontWeight: '500' as const,
    color: Colors.text,
  },
  caption: {
    fontSize: 12,
    fontWeight: '500' as const,
    color: Colors.textMuted,
  },
  mono: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: Colors.accent,
  },
};

export const Shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 8,
    elevation: 4,
  },
  glowCyan: {
    shadowColor: Colors.accent,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.45,
    shadowRadius: 10,
    elevation: 6,
  },
  glowGreen: {
    shadowColor: Colors.gradeA,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 5,
  },
};
