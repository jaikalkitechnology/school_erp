import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Brand tokens lifted from school_erp_designed/jaikalki-school-erp-design.html.
/// Keep this file the single source of truth for colours / typography on mobile.
class JaikalkiBrand {
  static const saffron = Color(0xFFE85D2E);
  static const saffronDark = Color(0xFFC44419);
  static const saffronDarker = Color(0xFF8C2F0E);
  static const saffronLight = Color(0xFFFF7A4D);
  static const saffronPale = Color(0xFFFEE5DA);

  static const teal = Color(0xFF0F766E);
  static const tealDark = Color(0xFF115E59);
  static const tealPale = Color(0xFFD1F0EC);

  static const marigold = Color(0xFFFFB800);
  static const marigoldBright = Color(0xFFFFC72E);
  static const marigoldPale = Color(0xFFFFF3D6);

  static const indigo = Color(0xFF2E1A6B);
  static const indigoDark = Color(0xFF1F1248);

  static const ivory = Color(0xFFFFF9F0);
  static const warmWhite = Color(0xFFFFFCF7);
  static const textSecondary = Color(0xFF4C4068);

  static ThemeData lightTheme() {
    final colorScheme = ColorScheme(
      brightness: Brightness.light,
      primary: saffron,
      onPrimary: warmWhite,
      secondary: teal,
      onSecondary: warmWhite,
      tertiary: marigold,
      onTertiary: indigoDark,
      error: const Color(0xFFDC2626),
      onError: warmWhite,
      surface: warmWhite,
      onSurface: indigoDark,
      surfaceContainerHighest: ivory,
      outline: const Color(0xFFE5DFD0),
    );

    final textTheme = TextTheme(
      displayLarge: GoogleFonts.fraunces(fontSize: 40, fontWeight: FontWeight.w600, color: indigoDark, height: 1.1),
      displayMedium: GoogleFonts.fraunces(fontSize: 32, fontWeight: FontWeight.w600, color: indigoDark),
      headlineMedium: GoogleFonts.fraunces(fontSize: 24, fontWeight: FontWeight.w600, color: indigoDark),
      titleLarge: GoogleFonts.fraunces(fontSize: 20, fontWeight: FontWeight.w600, color: indigoDark),
      titleMedium: GoogleFonts.dmSans(fontSize: 16, fontWeight: FontWeight.w600, color: indigoDark),
      bodyLarge: GoogleFonts.dmSans(fontSize: 15, color: indigoDark),
      bodyMedium: GoogleFonts.dmSans(fontSize: 14, color: textSecondary),
      labelLarge: GoogleFonts.dmSans(fontSize: 13, fontWeight: FontWeight.w600, letterSpacing: 0.5),
      labelSmall: GoogleFonts.jetBrainsMono(fontSize: 11, letterSpacing: 1.6, color: saffronDark),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: ivory,
      textTheme: textTheme,
      appBarTheme: AppBarTheme(
        backgroundColor: warmWhite,
        foregroundColor: indigoDark,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.fraunces(fontSize: 20, fontWeight: FontWeight.w600, color: indigoDark),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: saffron,
          foregroundColor: warmWhite,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: GoogleFonts.dmSans(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: warmWhite,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE5DFD0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: saffron, width: 2),
        ),
      ),
      cardTheme: CardThemeData(
        color: warmWhite,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: saffronPale),
        ),
      ),
    );
  }
}
