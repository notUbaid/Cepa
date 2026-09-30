/**
 * CEPA Unified Design System — Multi-Platform Design Tokens
 * Harmonized across Web Inspector Studio and React Native Mobile Workstation.
 * 
 * Architecture:
 * - 10-Step Tonal Ramps: Neutral (Obsidian Zinc), Ruby (Allium Cepa Cultivar),
 *   Emerald (Certified Grade A), Amber (URS / Mandi FAQ), Rose (Pathology / Reject),
 *   and Sky (Caliper & Telemetry Laser).
 * - Semantic Surface Tokens: High-contrast Dark & Warm Editorial Light Modes.
 * - Architectural Micro-Radii & Multi-Layer Elevation Shadows.
 * - Strict Typography Scale: Inter & JetBrains Mono pairing.
 */

// ── 1. TONAL COLOR RAMPS (10-STEP SCALES) ──

export const Neutral = {
  50: '#fafafa',
  100: '#f4f4f5',
  200: '#e4e4e7',
  300: '#d4d4d8',
  400: '#a1a1aa',
  500: '#71717a',
  600: '#52525b',
  700: '#3f3f46',
  800: '#27272a',
  900: '#18181b',
  950: '#09090b',
} as const;

export const Ruby = {
  50: '#fdf2f4',
  100: '#fbe6e9',
  200: '#f7ccd4',
  300: '#f0a3b3',
  400: '#e46f88',
  500: '#d44365',
  600: '#bd284f',
  700: '#9f1d3e',
  800: '#841b37',
  900: '#701a32',
} as const;

export const Emerald = {
  50: '#ecfdf5',
  100: '#d1fae5',
  200: '#a7f3d0',
  300: '#6ee7b7',
  400: '#34d399',
  500: '#10b981',
  600: '#059669',
  700: '#047857',
  800: '#065f46',
  900: '#064e3b',
} as const;

export const Amber = {
  50: '#fffbeb',
  100: '#fef3c7',
  200: '#fde68a',
  300: '#fcd34d',
  400: '#fbbf24',
  500: '#f59e0b',
  600: '#d97706',
  700: '#b45309',
  800: '#92400e',
  900: '#78350f',
} as const;

export const Rose = {
  50: '#fff1f2',
  100: '#ffe4e6',
  200: '#fecdd3',
  300: '#fda4af',
  400: '#fb7185',
  500: '#f43f5e',
  600: '#e11d48',
  700: '#be123c',
  800: '#9f1239',
  900: '#881337',
} as const;

export const Sky = {
  50: '#f0f9ff',
  100: '#e0f2fe',
  200: '#bae6fd',
  300: '#7dd3fc',
  400: '#38bdf8',
  500: '#0ea5e9',
  600: '#0284c7',
  700: '#0369a1',
  800: '#075985',
  900: '#0c4a6e',
} as const;

// ── 2. SEMANTIC PALETTES ──

export const DarkTheme = {
  surfaceCanvas: Neutral[950],         // #09090b
  surfaceBase: '#121215',              // Primary workstation background
  surfaceCard: '#18181c',              // Elevated cards
  surfaceElevated: '#202026',          // Interactive hover/active surfaces
  surfaceOverlay: 'rgba(9, 9, 11, 0.85)',

  borderSubtle: 'rgba(255, 255, 255, 0.08)',
  borderDefault: 'rgba(255, 255, 255, 0.12)',
  borderStrong: 'rgba(255, 255, 255, 0.20)',
  borderFocus: Sky[500],

  textPrimary: '#f4f4f6',
  textSecondary: Neutral[400],
  textMuted: Neutral[500],
  textDim: Neutral[600],
  textInverted: Neutral[950],

  brandPrimary: Ruby[600],
  brandAccent: Ruby[400],
  brandGlow: 'rgba(189, 40, 79, 0.35)',

  statusCertified: Emerald[500],
  statusCertifiedBg: 'rgba(16, 185, 129, 0.12)',
  statusReview: Sky[500],
  statusReviewBg: 'rgba(14, 165, 233, 0.12)',
  statusReject: Rose[500],
  statusRejectBg: 'rgba(244, 63, 94, 0.12)',
  statusDraft: Neutral[500],
  statusDraftBg: 'rgba(113, 113, 122, 0.12)',
  statusUrs: Amber[500],
  statusUrsBg: 'rgba(245, 158, 11, 0.12)',
} as const;

export const LightTheme = {
  surfaceCanvas: '#f4f3ef',
  surfaceBase: '#f8f7f4',              // Warm tactile editorial background
  surfaceCard: '#ffffff',              // Pure white card
  surfaceElevated: '#f4f3ef',
  surfaceOverlay: 'rgba(255, 255, 255, 0.94)',

  borderSubtle: '#eeebe5',
  borderDefault: '#e5e2db',
  borderStrong: '#d4cfc7',
  borderFocus: Sky[600],

  textPrimary: '#0c0c0e',
  textSecondary: '#475569',
  textMuted: '#64748b',
  textDim: '#94a3b8',
  textInverted: '#ffffff',

  brandPrimary: Ruby[700],
  brandAccent: Ruby[500],
  brandGlow: 'rgba(189, 40, 79, 0.20)',

  statusCertified: Emerald[700],
  statusCertifiedBg: Emerald[50],
  statusReview: Sky[700],
  statusReviewBg: Sky[50],
  statusReject: Rose[700],
  statusRejectBg: Rose[50],
  statusDraft: Neutral[600],
  statusDraftBg: Neutral[100],
  statusUrs: Amber[700],
  statusUrsBg: Amber[50],
} as const;

// ── 3. BACKWARD-COMPATIBLE RUNTIME COLORS OBJECT ──

export const Colors = {
  // Tonal Ramp Direct Access
  neutral: Neutral,
  ruby: Ruby,
  emerald: Emerald,
  amber: Amber,
  rose: Rose,
  sky: Sky,

  // Legacy Surfaces & Foundations
  bg: LightTheme.surfaceBase,
  bgDeep: DarkTheme.surfaceBase,
  canvasDark: DarkTheme.surfaceCanvas,
  cardBg: LightTheme.surfaceCard,
  cardBgElevated: LightTheme.surfaceElevated,
  cardBgHover: '#eeebe5',
  surfaceGlass: LightTheme.surfaceOverlay,
  surfaceDarkCard: DarkTheme.surfaceCard,
  surfaceDarkElevated: DarkTheme.surfaceElevated,

  // Borders
  border: LightTheme.borderDefault,
  borderActive: Neutral[900],
  borderMuted: LightTheme.borderSubtle,
  borderHighlight: LightTheme.borderStrong,
  borderDark: DarkTheme.borderDefault,
  borderDarkSubtle: DarkTheme.borderSubtle,

  // Accents & Brand Actions
  accent: Neutral[950],
  accentDark: '#050506',
  accentSubtle: Neutral[100],
  accentTeal: '#0f766e',
  accentCyan: Sky[500],
  accentAmber: Amber[600],
  accentRuby: Ruby[600],
  brand: Ruby[600],
  brandLight: Ruby[400],
  brandDark: Ruby[700],

  // Mandi Quality Assurance Statuses (BIS IS 17912 & NAFED PSF)
  gradeA: Emerald[700],
  gradeABg: Emerald[50],
  gradeABorder: Emerald[200],
  gradeADark: Emerald[500],
  gradeADarkBg: DarkTheme.statusCertifiedBg,

  urs: Amber[700],
  ursBg: Amber[50],
  ursBorder: Amber[200],
  ursDark: Amber[500],
  ursDarkBg: DarkTheme.statusUrsBg,

  reject: Rose[700],
  rejectBg: Rose[50],
  rejectBorder: Rose[200],
  rejectDark: Rose[500],
  rejectDarkBg: DarkTheme.statusRejectBg,

  review: Sky[700],
  reviewBg: Sky[50],
  reviewBorder: Sky[200],
  reviewDark: Sky[500],
  reviewDarkBg: DarkTheme.statusReviewBg,

  // Typography Tokens
  text: LightTheme.textPrimary,
  textSecondary: LightTheme.textSecondary,
  textMuted: LightTheme.textMuted,
  textDim: LightTheme.textDim,
  textInverted: '#ffffff',

  textDark: DarkTheme.textPrimary,
  textDarkSecondary: DarkTheme.textSecondary,
  textDarkMuted: DarkTheme.textMuted,

  // Skeleton & Overlay Tokens
  skeletonBase: '#e8e5de',
  skeletonHighlight: '#f5f3ed',
  skeletonDarkBase: '#202026',
  skeletonDarkHighlight: '#2a2a32',
  overlayDark: 'rgba(9, 9, 11, 0.75)',
};

// ── 4. SPACING SCALE (4px Base Grid) ──

export const Spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  hero: 32,
  section: 48,
} as const;

// ── 5. ARCHITECTURAL MICRO-RADIUS SCALE ──

export const Radius = {
  xs: 4,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  xxl: 20,
  pill: 6,                      // Precision architectural micro-radius
  circle: 9999,
} as const;

// ── 6. TYPOGRAPHY SYSTEM ──

export const Typography = {
  display: {
    fontSize: 28,
    fontWeight: '800' as const,
    color: Colors.text,
    letterSpacing: -0.6,
    lineHeight: 34,
  },
  hero: {
    fontSize: 24,
    fontWeight: '700' as const,
    color: Colors.text,
    letterSpacing: -0.4,
    lineHeight: 30,
  },
  title1: {
    fontSize: 20,
    fontWeight: '700' as const,
    color: Colors.text,
    letterSpacing: -0.3,
    lineHeight: 26,
  },
  title2: {
    fontSize: 16,
    fontWeight: '600' as const,
    color: Colors.text,
    letterSpacing: -0.2,
    lineHeight: 22,
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
    lineHeight: 20,
  },
  label: {
    fontSize: 13,
    fontWeight: '600' as const,
    color: Colors.text,
    letterSpacing: -0.1,
  },
  caption: {
    fontSize: 12,
    fontWeight: '500' as const,
    color: Colors.textMuted,
    lineHeight: 16,
  },
  subcaption: {
    fontSize: 10,
    fontWeight: '600' as const,
    color: Colors.textDim,
    letterSpacing: 0.4,
    textTransform: 'uppercase' as const,
  },
  mono: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: Colors.text,
    letterSpacing: 0.1,
  },
  monoBold: {
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: '700' as const,
    color: Colors.text,
  },
};

// ── 7. MULTI-LAYER DEPTH SHADOWS ──

export const Shadows = {
  sm: {
    shadowColor: '#09090b',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
  card: {
    shadowColor: '#09090b',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardElevated: {
    shadowColor: '#09090b',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.10,
    shadowRadius: 14,
    elevation: 5,
  },
  cardHover: {
    shadowColor: '#09090b',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.14,
    shadowRadius: 22,
    elevation: 8,
  },
  glowRuby: {
    shadowColor: '#bd284f',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 6,
  },
  glowGreen: {
    shadowColor: '#10b981',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  glowAmber: {
    shadowColor: '#f59e0b',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 4,
  },
  modal: {
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.20,
    shadowRadius: 28,
    elevation: 12,
  },
};
