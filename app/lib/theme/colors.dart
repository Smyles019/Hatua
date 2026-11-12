import 'package:flutter/material.dart';

/// Hatua colour tokens (Hatua design system, tokens.json), with a light and a dark value.
/// Dark mode uses deeper values of the same colours, never black or grey.
/// Orange and coral are reserved for risk states and never used decoratively.
///
/// Read them from a widget with `context.hc.plum700`, so they follow the theme.
@immutable
class HatuaPalette extends ThemeExtension<HatuaPalette> {
  const HatuaPalette({
    required this.plum900,
    required this.plum700,
    required this.plum500,
    required this.plum200,
    required this.plum100,
    required this.surfacePage,
    required this.surfaceCard,
    required this.muted,
    required this.onPrimary,
    required this.onBright,
    required this.header,
    required this.onHeader,
    required this.sun500,
    required this.sun100,
    required this.sky500,
    required this.sky100,
    required this.blush500,
    required this.blush100,
    required this.domainSocial,
    required this.riskLow,
    required this.riskLowBg,
    required this.riskLowText,
    required this.riskMedium,
    required this.riskMediumBg,
    required this.riskHigh,
    required this.riskHighBg,
    required this.sprout,
    required this.leaf,
    required this.shadow,
  });

  /// Main text and icons on page and card surfaces.
  final Color plum900;

  /// Primary: buttons, links, active nav, progress.
  final Color plum700;

  /// Decorative only (header circles, inactive accents). Never text.
  final Color plum500;

  /// Borders, dividers, the journey path line.
  final Color plum200;

  /// Input fields, nav bar, tinted cards.
  final Color plum100;
  final Color surfacePage;
  final Color surfaceCard;

  /// Secondary text.
  final Color muted;

  /// Text and icons on [plum700].
  final Color onPrimary;

  /// Text and icons on bright fills: sun, sky, blush, domain badges, orange and coral chips.
  final Color onBright;

  /// Blob header background and the text on it.
  final Color header;
  final Color onHeader;

  final Color sun500;
  final Color sun100;
  final Color sky500;
  final Color sky100;
  final Color blush500;
  final Color blush100;

  /// Social and emotional domain badge fill.
  final Color domainSocial;

  final Color riskLow;
  final Color riskLowBg;
  final Color riskLowText;
  final Color riskMedium;
  final Color riskMediumBg;
  final Color riskHigh;
  final Color riskHighBg;

  /// Sprout mascot body and leaves.
  final Color sprout;
  final Color leaf;

  /// Card shadow colour (transparent in dark mode: no shadows on dark plum).
  final Color shadow;

  static const light = HatuaPalette(
    plum900: Color(0xFF3A1F36),
    plum700: Color(0xFF7B3F70),
    plum500: Color(0xFFA86C9C),
    plum200: Color(0xFFE3CCDE),
    plum100: Color(0xFFF1E6EF),
    surfacePage: Color(0xFFFBF7FA),
    surfaceCard: Color(0xFFFFFFFF),
    muted: Color(0xFF6B5468),
    onPrimary: Color(0xFFFFFFFF),
    onBright: Color(0xFF3A1F36),
    header: Color(0xFF7B3F70),
    onHeader: Color(0xFFFFFFFF),
    sun500: Color(0xFFF9BE3D),
    sun100: Color(0xFFFDF0CF),
    sky500: Color(0xFF9DC5E9),
    sky100: Color(0xFFE3EFFA),
    blush500: Color(0xFFF8AFA8),
    blush100: Color(0xFFFDE8E6),
    domainSocial: Color(0xFFE3CCDE),
    riskLow: Color(0xFF6CC3A4),
    riskLowBg: Color(0xFFDDF2EA),
    riskLowText: Color(0xFF3A1F36),
    riskMedium: Color(0xFFF39318),
    riskMediumBg: Color(0xFFFDE5C6),
    riskHigh: Color(0xFFEA6360),
    riskHighBg: Color(0xFFFBDCDB),
    sprout: Color(0xFFF9BE3D),
    leaf: Color(0xFF6CC3A4),
    shadow: Color(0x143A1F36),
  );

  static const dark = HatuaPalette(
    plum900: Color(0xFFF5ECF3),
    plum700: Color(0xFFC98BBD),
    plum500: Color(0xFF8E5A84),
    plum200: Color(0xFF4A3049),
    plum100: Color(0xFF382439),
    surfacePage: Color(0xFF1E1220),
    surfaceCard: Color(0xFF2A1A2C),
    muted: Color(0xFFC4AFC0),
    onPrimary: Color(0xFF1E1220),
    onBright: Color(0xFF1E1220),
    header: Color(0xFF4E2547),
    onHeader: Color(0xFFFFFFFF),
    sun500: Color(0xFFD9A53A),
    // Pale yellow cards turn a soft dark blue in dark mode (as on the website): the
    // brown that a dark yellow gives looked muddy.
    sun100: Color(0xFF1F2D3D),
    sky500: Color(0xFF7FA9D1),
    sky100: Color(0xFF1F2D3D),
    blush500: Color(0xFFD9918A),
    blush100: Color(0xFF3D2224),
    domainSocial: Color(0xFFB08CAA),
    riskLow: Color(0xFF4FA888),
    riskLowBg: Color(0xFF1D3A31),
    riskLowText: Color(0xFF8FD9BC),
    riskMedium: Color(0xFFE68A1A),
    riskMediumBg: Color(0xFF43290F),
    riskHigh: Color(0xFFE0605D),
    riskHighBg: Color(0xFF4A1C1E),
    sprout: Color(0xFFE8B54A),
    leaf: Color(0xFF5FA88E),
    shadow: Color(0x00000000),
  );

  @override
  HatuaPalette copyWith() => this;

  @override
  HatuaPalette lerp(HatuaPalette? other, double t) {
    if (other == null) return this;
    Color l(Color a, Color b) => Color.lerp(a, b, t)!;
    return HatuaPalette(
      plum900: l(plum900, other.plum900),
      plum700: l(plum700, other.plum700),
      plum500: l(plum500, other.plum500),
      plum200: l(plum200, other.plum200),
      plum100: l(plum100, other.plum100),
      surfacePage: l(surfacePage, other.surfacePage),
      surfaceCard: l(surfaceCard, other.surfaceCard),
      muted: l(muted, other.muted),
      onPrimary: l(onPrimary, other.onPrimary),
      onBright: l(onBright, other.onBright),
      header: l(header, other.header),
      onHeader: l(onHeader, other.onHeader),
      sun500: l(sun500, other.sun500),
      sun100: l(sun100, other.sun100),
      sky500: l(sky500, other.sky500),
      sky100: l(sky100, other.sky100),
      blush500: l(blush500, other.blush500),
      blush100: l(blush100, other.blush100),
      domainSocial: l(domainSocial, other.domainSocial),
      riskLow: l(riskLow, other.riskLow),
      riskLowBg: l(riskLowBg, other.riskLowBg),
      riskLowText: l(riskLowText, other.riskLowText),
      riskMedium: l(riskMedium, other.riskMedium),
      riskMediumBg: l(riskMediumBg, other.riskMediumBg),
      riskHigh: l(riskHigh, other.riskHigh),
      riskHighBg: l(riskHighBg, other.riskHighBg),
      sprout: l(sprout, other.sprout),
      leaf: l(leaf, other.leaf),
      shadow: l(shadow, other.shadow),
    );
  }
}

extension HatuaPaletteContext on BuildContext {
  /// The Hatua palette for the current theme (light or dark).
  HatuaPalette get hc => Theme.of(this).extension<HatuaPalette>() ?? HatuaPalette.light;
}
