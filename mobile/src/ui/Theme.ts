/**
 * Cepa Mandi Design System — Off-White Editorial Palette
 * Grounded, human-centered aesthetic for agricultural procurement officers.
 * Zero neon glow, zero AI-slop gradients, high-legibility print contrast.
 */

export const Colors = {
  // Surfaces
  bg: '#f9f8f6',                // Warm linen off-white
  cardBg: '#ffffff',            // Pure white card
  cardBgElevated: '#f4f3ef',    // Subtle warm tinted surface
  cardBgHover: '#ecebe6',
  surfaceGlass: 'rgba(255, 255, 255, 0.94)',

  // Borders
  border: '#e7e5e4',            // Clean 1px light border (stone-200)
  borderActive: '#18181b',      // Focused solid charcoal
  borderMuted: '#f0eeea',       // Faint divider
  borderHighlight: '#d6d3d1',   // Stronger outline

  // Primary Actions
  accent: '#18181b',            // Deep obsidian / charcoal
  accentDark: '#09090b',
  accentSubtle: '#f4f4f5',
  accentTeal: '#0f766e',        // Calm agricultural teal accent

  // Mandi Quality Standards
  gradeA: '#166534',            // Forest green
  gradeABg: '#f0fdf4',          // Soft mint background
  gradeABorder: '#bbf7d0',

  urs: '#9a3412',               // Warm ochre / amber
  ursBg: '#fffbeb',             // Pale cream
  ursBorder: '#fde68a',

  reject: '#991b1b',            // Deep brick crimson
  rejectBg: '#fef2f2',          // Light rose
  rejectBorder: '#fecaca',

  review: '#3f3f46',            // Restrained charcoal
  reviewBg: '#f4f4f5',
  reviewBorder: '#e4e4e7',

  // Typography
  text: '#18181b',              // Near-black charcoal
  textSecondary: '#52525b',      // Subdued charcoal
  textMuted: '#71717a',          // Mid-gray caption
  textDim: '#a1a1aa',            // Light gray

  // Skeleton Loaders
  skeletonBase: '#ece9e3',
  skeletonHighlight: '#f7f6f2',
  overlayDark: 'rgba(24, 24, 27, 0.65)',
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
  pill: 9999,
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
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  cardHover: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 6,
    elevation: 2,
  },
  modal: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.08,
    shadowRadius: 16,
    elevation: 8,
  },
};
