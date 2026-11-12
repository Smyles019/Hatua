import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'colors.dart';

/// Spacing and radius tokens.
class Space {
  Space._();
  static const s1 = 4.0;
  static const s2 = 8.0;
  static const s3 = 12.0;
  static const s4 = 16.0;
  static const s6 = 24.0;
  static const s8 = 32.0;
  static const touch = 48.0;
}

class Radii {
  Radii._();
  static const sm = 8.0;
  static const md = 14.0;
  static const lg = 20.0;
  static const xl = 28.0;
}

/// Card shadow for the current theme (none in dark mode).
List<BoxShadow> cardShadowOf(BuildContext context) =>
    [BoxShadow(color: context.hc.shadow, blurRadius: 10, offset: const Offset(0, 2))];

ThemeData buildHatuaTheme(Brightness brightness) {
  final p = brightness == Brightness.dark ? HatuaPalette.dark : HatuaPalette.light;
  final base = ThemeData(brightness: brightness, useMaterial3: true);
  final body = GoogleFonts.atkinsonHyperlegibleTextTheme(base.textTheme);
  TextStyle head(double size, double height, FontWeight w) => GoogleFonts.nunito(
      fontSize: size, height: height / size, fontWeight: w, color: p.plum900);
  TextStyle text(double size, double height, FontWeight w) => GoogleFonts.atkinsonHyperlegible(
      fontSize: size, height: height / size, fontWeight: w, color: p.plum900);

  final textTheme = body.copyWith(
    displaySmall: head(32, 38, FontWeight.w800),
    headlineSmall: head(24, 30, FontWeight.w800),
    titleLarge: head(20, 26, FontWeight.w700),
    titleMedium: head(17, 24, FontWeight.w700),
    bodyLarge: text(18, 27, FontWeight.w400),
    bodyMedium: text(16, 24, FontWeight.w400),
    bodySmall: text(14, 20, FontWeight.w400).copyWith(color: p.muted),
    labelLarge: text(16, 20, FontWeight.w700),
    labelMedium: text(13, 16, FontWeight.w700).copyWith(letterSpacing: 0.8, color: p.muted),
  );

  final scheme = ColorScheme(
    brightness: brightness,
    primary: p.plum700,
    onPrimary: p.onPrimary,
    secondary: p.sun500,
    onSecondary: p.onBright,
    error: p.riskHigh,
    onError: p.onBright,
    surface: p.surfaceCard,
    onSurface: p.plum900,
  );

  final fieldBorder = OutlineInputBorder(
    borderRadius: BorderRadius.circular(Radii.md),
    borderSide: BorderSide(color: p.plum200, width: 1.5),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    extensions: [p],
    scaffoldBackgroundColor: p.surfacePage,
    canvasColor: p.surfacePage,
    textTheme: textTheme,
    iconTheme: IconThemeData(color: p.plum900),
    appBarTheme: AppBarTheme(
      backgroundColor: p.surfacePage,
      foregroundColor: p.plum900,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: textTheme.titleMedium,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: p.plum100,
      contentPadding: const EdgeInsets.symmetric(horizontal: Space.s4, vertical: 14),
      border: fieldBorder,
      enabledBorder: fieldBorder,
      focusedBorder: fieldBorder.copyWith(borderSide: BorderSide(color: p.plum700, width: 2)),
      errorBorder: fieldBorder.copyWith(borderSide: BorderSide(color: p.riskHigh, width: 1.5)),
      focusedErrorBorder:
          fieldBorder.copyWith(borderSide: BorderSide(color: p.riskHigh, width: 2)),
      hintStyle: textTheme.bodyMedium?.copyWith(color: p.muted),
      errorStyle: textTheme.bodySmall?.copyWith(color: p.plum900),
      prefixIconColor: p.plum900,
      suffixIconColor: p.plum900,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: p.plum700,
        foregroundColor: p.onPrimary,
        minimumSize: const Size.fromHeight(Space.touch),
        shape: const StadiumBorder(),
        textStyle: textTheme.labelLarge,
        disabledBackgroundColor: p.plum100,
        disabledForegroundColor: p.muted,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size.fromHeight(Space.touch),
        shape: const StadiumBorder(),
        foregroundColor: p.plum700,
        side: BorderSide(color: p.plum200, width: 2),
        textStyle: textTheme.labelLarge,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(Space.touch, Space.touch),
        foregroundColor: p.plum700,
        textStyle: textTheme.labelLarge?.copyWith(decoration: TextDecoration.underline),
      ),
    ),
    dialogTheme: DialogThemeData(backgroundColor: p.surfaceCard),
    bottomSheetTheme: BottomSheetThemeData(backgroundColor: p.surfaceCard),
    datePickerTheme: DatePickerThemeData(backgroundColor: p.surfaceCard),
    popupMenuTheme: PopupMenuThemeData(color: p.surfaceCard),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: p.plum700),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: p.plum900,
      contentTextStyle: textTheme.bodyMedium?.copyWith(color: p.surfacePage),
      behavior: SnackBarBehavior.floating,
    ),
    dividerColor: p.plum200,
  );
}

/// Secondary (sun) pill button style.
ButtonStyle secondaryButtonStyle(BuildContext context) => FilledButton.styleFrom(
      backgroundColor: context.hc.sun500,
      foregroundColor: context.hc.onBright,
    );
