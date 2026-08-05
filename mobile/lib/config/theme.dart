/// Cognimap Light Theme — Chart paper & pencil aesthetic.
library;

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  AppColors._();

  // ── Core surfaces (Paper) ────────────────────────────────
  static const Color background = Color(0xFFFFFDF8); // Warm, yellow-tinted chart paper
  static const Color surface = Color(0xFFFFFFFF); // Pure white for cards to pop against paper
  static const Color surface2 = Color(0xFFFEF3C7); // Light Yellow sticky note
  static const Color border = Color(0xFFCBD5E1); // Darker pencil border
  static const Color borderHover = Color(0xFF475569);

  // ── Primary (Graphite/Ink) ──────────────────────────────
  static const Color primary50 = Color(0xFFE2E8F0);
  static const Color primary100 = Color(0xFFCBD5E1);
  static const Color primary200 = Color(0xFF94A3B8);
  static const Color primary300 = Color(0xFF64748B);
  static const Color primary400 = Color(0xFF475569);
  static const Color primary500 = Color(0xFF1E293B); // Bold black ink
  static const Color primary600 = Color(0xFF0F172A);
  static const Color primary700 = Color(0xFF000000);

  // ── Accent (Highlighter) ────────────────────────────────
  static const Color accent400 = Color(0xFF38BDF8); // Bright blue marker
  static const Color accent500 = Color(0xFF0EA5E9);
  static const Color accent600 = Color(0xFF0284C7);

  // ── Semantic ────────────────────────────────────────────
  static const Color success = Color(0xFF16A34A); // Bright green ink
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFDC2626); // Bright red ink

  // ── Text ────────────────────────────────────────────────
  static const Color textPrimary = Color(0xFF000000); // Pure black ink for highest contrast
  static const Color textSecondary = Color(0xFF334155); // Dark graphite
  static const Color textMuted = Color(0xFF64748B);
  static const Color textDisabled = Color(0xFF94A3B8);
  
  // ── Grid Lines ──────────────────────────────────────────
  static const Color gridLine = Color(0xFFE0F2FE); // Very faint cyan grid line
  static const Color gridLineMargin = Color(0xFFFECACA); // Faint red margin line
}

ThemeData buildAppTheme() {
  final base = ThemeData.light(useMaterial3: true);
  
  // Use a clean font for the UI headers, we will use Caveat for the study text.
  final textTheme = GoogleFonts.kalamTextTheme(base.textTheme);

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.background,
    splashFactory: InkSparkle.splashFactory,
    visualDensity: VisualDensity.standard,
    colorScheme: const ColorScheme.light(
      primary: AppColors.primary500,
      onPrimary: Colors.white,
      secondary: AppColors.accent500,
      onSecondary: AppColors.textPrimary,
      surface: AppColors.surface,
      onSurface: AppColors.textPrimary,
      error: AppColors.error,
      onError: Colors.white,
    ),
    textTheme: textTheme.apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    ),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 4,
      shadowColor: AppColors.primary700.withOpacity(0.15),
      margin: const EdgeInsets.symmetric(vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: AppColors.primary200, width: 1),
      ),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      titleTextStyle: textTheme.titleLarge?.copyWith(
        color: AppColors.textPrimary,
        fontWeight: FontWeight.w700,
        fontSize: 24,
      ),
      iconTheme: const IconThemeData(color: AppColors.primary500),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.transparent,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: AppColors.primary500, width: 2),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: AppColors.primary400, width: 1.5),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: AppColors.primary600, width: 2.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: AppColors.error, width: 2),
      ),
      hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 16),
      labelStyle: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primary500,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        elevation: 8,
        shadowColor: AppColors.primary700.withOpacity(0.4),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: const BorderSide(color: AppColors.primary700, width: 3),
        ),
        textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.textPrimary,
        side: const BorderSide(color: AppColors.primary500, width: 2),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
      ),
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: AppColors.primary600,
      contentTextStyle: textTheme.bodyMedium?.copyWith(color: Colors.white),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: AppColors.primary700, width: 2),
      ),
      behavior: SnackBarBehavior.floating,
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: AppColors.background,
      elevation: 24,
      shadowColor: AppColors.primary700,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(0)),
        side: BorderSide(color: AppColors.primary500, width: 4),
      ),
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.primary200,
      thickness: 1.5,
    ),
    chipTheme: ChipThemeData(
      backgroundColor: AppColors.background,
      selectedColor: AppColors.accent400,
      side: const BorderSide(color: AppColors.primary500, width: 1.5),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
      labelStyle: const TextStyle(color: AppColors.textPrimary, fontSize: 14, fontWeight: FontWeight.w600),
    ),
  );
}
