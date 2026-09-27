/**
 * Cepa Mandi Design System — Off-White Editorial Palette
 * Grounded, human-centered aesthetic for agricultural procurement officers.
 * Zero neon glow, zero AI-slop gradients, high-legibility print contrast.
 */

export const Colors = {
  // Surfaces
  bg: '#f8f7f4',                // Warm tactile editorial background
  bgDeep: '#0c0c0e',            // Obsidian dark hero surfaces
  cardBg: '#ffffff',            // Pure white card
  cardBgElevated: '#f4f3ef',    // Subtle warm tinted surface
  cardBgHover: '#eeebe5',
  surfaceGlass: 'rgba(255, 255, 255, 0.94)',

  // Borders
  border: '#e5e2db',            // Crisp light border
  borderActive: '#18181b',      // Focused solid charcoal
  borderMuted: '#eeebe5',       // Faint divider
  borderHighlight: '#d4cfc7',   // Stronger outline

  // Primary Actions & Accents
  accent: '#0c0c0e',            // Deep obsidian
  accentDark: '#050506',
  accentSubtle: '#f4f4f5',
  accentTeal: '#0f766e',        // Calm agricultural teal accent
  accentCyan: '#0284c7',        // Caliper laser cyan
  accentAmber: '#d97706',       // APMC harvest amber
  accentRuby: '#be123c',        // Onion skin ruby

  // Mandi Quality Standards — Vibrant, Prestigious & High-Contrast
  gradeA: '#047857',            // Emerald green for certified Grade A
  gradeABg: '#ecfdf5',          // Soft crisp mint
  gradeABorder: '#a7f3d0',      // Mint border

  urs: '#b45309',               // Warm ochre / amber for Under Rejection Standard
  ursBg: '#fffbeb',             // Soft warm gold
  ursBorder: '#fde68a',

  reject: '#b91c1c',            // Deep brick crimson for rejects
  rejectBg: '#fef2f2',          // Light rose
  rejectBorder: '#fecaca',

  review: '#0369a1',            // Technical cyan for in-review / pending
  reviewBg: '#f0f9ff',
  reviewBorder: '#bae6fd',

  // Typography
  text: '#0c0c0e',              // Near-black charcoal
  textSecondary: '#475569',      // Slate charcoal
  textMuted: '#64748b',          // Mid-slate caption
  textDim: '#94a3b8',            // Light slate
  textInverted: '#ffffff',

  // Skeleton Loaders
  skeletonBase: '#e8e5de',
  skeletonHighlight: '#f5f3ed',
  overlayDark: 'rgba(12, 12, 14, 0.72)',
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
  md: 8,
  lg: 12,
  xl: 16,
  pill: 4,                      // Abolished 9999px capsule; architectural micro-radius
};

export const Typography = {
  hero: {
    fontSize: 26,
    fontWeight: '700' as const,
    color: Colors.text,
    letterSpacing: -0.4,
  },
  title1: {
    fontSize: 20,
    fontWeight: '700' as const,
    color: Colors.text,
    letterSpacing: -0.3,
  },
  title2: {
    fontSize: 16,
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
    color: Colors.text,
  },
};

export const Shadows = {
  sm: {
    shadowColor: '#0c0a09',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  card: {
    shadowColor: '#0c0a09',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 3,
  },
  cardElevated: {
    shadowColor: '#0c0a09',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 5,
  },
  cardHover: {
    shadowColor: '#0c0a09',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 20,
    elevation: 8,
  },
  glowGreen: {
    shadowColor: '#059669',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  glowAmber: {
    shadowColor: '#d97706',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  modal: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.14,
    shadowRadius: 24,
    elevation: 10,
  },
};
