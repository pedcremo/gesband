import 'package:flutter/material.dart';

import 'brand.dart';
import 'color_contrast.dart';
import 'visual_style.dart';

/// Neutros y colores de estado de un estilo en un modo.
class _Palette {
  const _Palette({
    required this.background,
    required this.surface,
    required this.surfaceMuted,
    required this.ink,
    required this.muted,
    required this.line,
    required this.staff,
    required this.success,
    required this.successInk,
    required this.warning,
    required this.warningInk,
    required this.danger,
    required this.dangerInk,
  });

  final Color background;
  final Color surface;
  final Color surfaceMuted;
  final Color ink;
  final Color muted;
  final Color line;
  final Color staff;
  final Color success;
  final Color successInk;
  final Color warning;
  final Color warningInk;
  final Color danger;
  final Color dangerInk;
}

// Escenario: valores de B-Agenda.dc.html.
const _escenarioDark = _Palette(
  background: Color(0xFF0F1012),
  surface: Color(0xFF1B1D21),
  surfaceMuted: Color(0xFF26292E),
  ink: Color(0xFFF2F2F0),
  muted: Color(0xFFA3A6AD),
  line: Color(0xFF2C2F35),
  staff: Color(0xFF3A3E46),
  success: Color(0xFF163A24),
  successInk: Color(0xFF9BE3B1),
  warning: Color(0xFF3A2E10),
  warningInk: Color(0xFFF5D27A),
  danger: Color(0xFF3A1A1A),
  dangerInk: Color(0xFFF2A7A7),
);

const _escenarioLight = _Palette(
  background: Color(0xFFF4F4F2),
  surface: Color(0xFFFFFFFF),
  surfaceMuted: Color(0xFFECEDEA),
  ink: Color(0xFF111214),
  muted: Color(0xFF5C5F66),
  line: Color(0xFFDADBD8),
  staff: Color(0xFFC9CAC6),
  success: Color(0xFFDDF3E4),
  successInk: Color(0xFF1D5A33),
  warning: Color(0xFFFBEFCF),
  warningInk: Color(0xFF6A4B0B),
  danger: Color(0xFFF8E0E0),
  dangerInk: Color(0xFF7A2626),
);

// Partitura: papel de Main.dc.html; el oscuro es su versión nocturna.
const _partituraLight = _Palette(
  background: Color(0xFFFBFAF7),
  surface: Color(0xFFFFFFFF),
  surfaceMuted: Color(0xFFF3F0E9),
  ink: Color(0xFF1E1B18),
  muted: Color(0xFF6B645A),
  line: Color(0xFFE6E1D6),
  staff: Color(0xFFCFC8BA),
  success: Color(0xFFE3EEE5),
  successInk: Color(0xFF23502E),
  warning: Color(0xFFF6EBD3),
  warningInk: Color(0xFF6A4B0B),
  danger: Color(0xFFEFE9E9),
  dangerInk: Color(0xFF5E2A2A),
);

const _partituraDark = _Palette(
  background: Color(0xFF171512),
  surface: Color(0xFF211E1A),
  surfaceMuted: Color(0xFF2B2722),
  ink: Color(0xFFF3EFE7),
  muted: Color(0xFFADA597),
  line: Color(0xFF36312A),
  staff: Color(0xFF4A443B),
  success: Color(0xFF1E3324),
  successInk: Color(0xFFA9D8B4),
  warning: Color(0xFF3A2F17),
  warningInk: Color(0xFFEBCF8A),
  danger: Color(0xFF3B2222),
  dangerInk: Color(0xFFE7AFAF),
);

// Festa: valores de C-Agenda.dc.html; el oscuro conserva su calidez.
const _festaLight = _Palette(
  background: Color(0xFFF5F6FA),
  surface: Color(0xFFFFFFFF),
  surfaceMuted: Color(0xFFECEEF3),
  ink: Color(0xFF16181D),
  muted: Color(0xFF555A66),
  line: Color(0xFFE3E5EC),
  staff: Color(0xFFCDD1DB),
  success: Color(0xFFDDF3E4),
  successInk: Color(0xFF1D5A33),
  warning: Color(0xFFFBEFCF),
  warningInk: Color(0xFF6A4B0B),
  danger: Color(0xFFF8E0E0),
  dangerInk: Color(0xFF7A2626),
);

const _festaDark = _Palette(
  background: Color(0xFF121419),
  surface: Color(0xFF1C1F26),
  surfaceMuted: Color(0xFF272B34),
  ink: Color(0xFFF1F2F6),
  muted: Color(0xFFA4A9B6),
  line: Color(0xFF2D313B),
  staff: Color(0xFF3B404C),
  success: Color(0xFF163A24),
  successInk: Color(0xFF9BE3B1),
  warning: Color(0xFF3A2E10),
  warningInk: Color(0xFFF5D27A),
  danger: Color(0xFF3A1A1A),
  dangerInk: Color(0xFFF2A7A7),
);

/// Contraste por debajo del cual una superficie se confunde con el fondo.
const double minimumSurfaceContrast = 1.5;

/// Borde para las superficies rellenas del color principal.
///
/// Si el principal no alcanza 1.5:1 con el fondo o la superficie del modo
/// (p. ej. una banda negra, #111111, en oscuro), esas superficies llevan un
/// borde del secundario; si el secundario tampoco contrasta, de la línea del
/// tema. Devuelve `null` si el principal ya se distingue.
Color? primaryEdgeFor({
  required Color primary,
  required Color secondary,
  required Color background,
  required Color surface,
  required Color line,
}) {
  bool blends(Color color) =>
      contrastRatio(color, background) < minimumSurfaceContrast ||
      contrastRatio(color, surface) < minimumSurfaceContrast;
  if (!blends(primary)) return null;
  return blends(secondary) ? line : secondary;
}

/// Familias tipográficas empaquetadas en `assets/fonts` (ver pubspec.yaml).
abstract final class GesbandFonts {
  static const bigShouldersDisplay = 'BigShouldersDisplay';
  static const instrumentSans = 'InstrumentSans';
  static const libreCaslonText = 'LibreCaslonText';
  static const publicSans = 'PublicSans';
  static const bricolageGrotesque = 'BricolageGrotesque';
  static const figtree = 'Figtree';
}

/// Espaciados comunes a los tres estilos (múltiplos de 4).
abstract final class GesbandSpacing {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 20.0;
  static const xxl = 24.0;
  static const xxxl = 32.0;

  /// Altura mínima de una diana táctil.
  static const minTarget = 48.0;
}

/// Tokens del sistema visual: colores, tipografías y radios de un estilo en
/// un modo, ya combinados con la marca. Las pantallas los leen con
/// `GesbandTokens.of(context)` y nunca escriben colores ni fuentes a mano.
@immutable
class GesbandTokens extends ThemeExtension<GesbandTokens> {
  const GesbandTokens({
    required this.style,
    required this.brightness,
    required this.background,
    required this.surface,
    required this.surfaceMuted,
    required this.ink,
    required this.muted,
    required this.line,
    required this.staff,
    required this.primary,
    required this.onPrimary,
    required this.primaryText,
    required this.primaryOnInk,
    required this.primaryTint,
    required this.onPrimaryTint,
    required this.secondary,
    required this.onSecondary,
    required this.highlight,
    required this.primaryEdge,
    required this.success,
    required this.successInk,
    required this.warning,
    required this.warningInk,
    required this.danger,
    required this.dangerInk,
    required this.displayFamily,
    required this.bodyFamily,
    required this.displayWeight,
    required this.displayUppercase,
    required this.displayHeight,
    required this.displayTracking,
    required this.radiusSmall,
    required this.radiusCard,
    required this.radiusLarge,
    required this.radiusButton,
    required this.radiusNav,
  });

  /// Combina el estilo de la marca, el modo y sus colores.
  factory GesbandTokens.resolve(Brand brand, Brightness brightness) {
    final dark = brightness == Brightness.dark;
    final palette = switch (brand.style) {
      VisualStyle.escenario => dark ? _escenarioDark : _escenarioLight,
      VisualStyle.partitura => dark ? _partituraDark : _partituraLight,
      VisualStyle.festa => dark ? _festaDark : _festaLight,
    };
    final primary = brand.primary.withValues(alpha: 1);
    final secondary = brand.secondary.withValues(alpha: 1);
    final onPrimary = readableInk(primary, dark: palette.ink.darkest);
    final tint = Color.alphaBlend(
        primary.withValues(alpha: dark ? 0.22 : 0.12), palette.surface);
    final typography = switch (brand.style) {
      VisualStyle.escenario => (
          GesbandFonts.bigShouldersDisplay,
          GesbandFonts.instrumentSans,
          FontWeight.w800,
          true,
          0.95,
          0.02,
        ),
      VisualStyle.partitura => (
          GesbandFonts.libreCaslonText,
          GesbandFonts.publicSans,
          FontWeight.w400,
          false,
          1.15,
          0.0,
        ),
      VisualStyle.festa => (
          GesbandFonts.bricolageGrotesque,
          GesbandFonts.figtree,
          FontWeight.w800,
          false,
          1.05,
          -0.01,
        ),
    };
    final radii = switch (brand.style) {
      VisualStyle.escenario => (10.0, 16.0, 20.0, 14.0, 22.0),
      VisualStyle.partitura => (6.0, 14.0, 14.0, 10.0, 0.0),
      VisualStyle.festa => (16.0, 24.0, 24.0, 999.0, 24.0),
    };
    return GesbandTokens(
      style: brand.style,
      brightness: brightness,
      background: palette.background,
      surface: palette.surface,
      surfaceMuted: palette.surfaceMuted,
      ink: palette.ink,
      muted: palette.muted,
      line: palette.line,
      staff: palette.staff,
      primary: primary,
      onPrimary: onPrimary,
      primaryText: legibleOn(primary, palette.background),
      primaryOnInk: legibleOn(primary, onPrimary),
      primaryTint: tint,
      onPrimaryTint: legibleOn(primary, tint),
      secondary: secondary,
      onSecondary: readableInk(secondary, dark: palette.ink.darkest),
      // Borde de lo que pide atención: 3:1, el mínimo de un elemento gráfico.
      highlight: legibleOn(secondary, palette.surface, minimum: 3),
      primaryEdge: primaryEdgeFor(
        primary: primary,
        secondary: secondary,
        background: palette.background,
        surface: palette.surface,
        line: palette.line,
      ),
      success: palette.success,
      successInk: palette.successInk,
      warning: palette.warning,
      warningInk: palette.warningInk,
      danger: palette.danger,
      dangerInk: palette.dangerInk,
      displayFamily: typography.$1,
      bodyFamily: typography.$2,
      displayWeight: typography.$3,
      displayUppercase: typography.$4,
      displayHeight: typography.$5,
      displayTracking: typography.$6,
      radiusSmall: radii.$1,
      radiusCard: radii.$2,
      radiusLarge: radii.$3,
      radiusButton: radii.$4,
      radiusNav: radii.$5,
    );
  }

  /// Tokens del tema. Sin la extensión (un `MaterialApp` sin el tema de
  /// Gesband, p. ej. en pruebas aisladas) se usa la marca de Gesband.
  static GesbandTokens of(BuildContext context) {
    final theme = Theme.of(context);
    return theme.extension<GesbandTokens>() ??
        (theme.brightness == Brightness.dark ? _fallbackDark : _fallbackLight);
  }

  static final _fallbackLight =
      GesbandTokens.resolve(Brand.gesband, Brightness.light);
  static final _fallbackDark =
      GesbandTokens.resolve(Brand.gesband, Brightness.dark);

  final VisualStyle style;
  final Brightness brightness;

  final Color background;
  final Color surface;
  final Color surfaceMuted;
  final Color ink;
  final Color muted;
  final Color line;

  /// Líneas del pentagrama de Partitura.
  final Color staff;

  /// Color principal tal cual, solo para fondos.
  final Color primary;

  /// Tinta legible encima de [primary].
  final Color onPrimary;

  /// Color principal corregido para texto sobre [background].
  final Color primaryText;

  /// Color principal corregido para texto sobre [onPrimary] (botón invertido
  /// del cartel).
  final Color primaryOnInk;

  /// Tinte suave del principal sobre [surface] y su texto legible.
  final Color primaryTint;
  final Color onPrimaryTint;

  final Color secondary;
  final Color onSecondary;

  /// Secundario corregido para bordes que llaman la atención.
  final Color highlight;

  /// Borde de las superficies rellenas del principal (cartel, píldora activa,
  /// bloque del logotipo, botones) cuando el principal se confunde con el
  /// fondo; `null` si no hace falta. Ver [primaryEdgeFor].
  final Color? primaryEdge;

  /// Grosor de [primaryEdge].
  static const primaryEdgeWidth = 2.0;

  /// Lado de borde listo para usar; `BorderSide.none` si no hace falta.
  BorderSide get primaryEdgeSide => primaryEdge == null
      ? BorderSide.none
      : BorderSide(color: primaryEdge!, width: primaryEdgeWidth);

  final Color success;
  final Color successInk;
  final Color warning;
  final Color warningInk;
  final Color danger;
  final Color dangerInk;

  final String displayFamily;
  final String bodyFamily;
  final FontWeight displayWeight;
  final bool displayUppercase;
  final double displayHeight;

  /// Espaciado entre letras de la tipografía de display, en em.
  final double displayTracking;

  final double radiusSmall;
  final double radiusCard;
  final double radiusLarge;
  final double radiusButton;
  final double radiusNav;

  bool get isDark => brightness == Brightness.dark;

  /// Sombra suave de Festa en claro (6 % de su tinta).
  Color get shadow => const Color(0x0F16181D);

  /// Estilo de display (nombres, fechas y títulos) a un tamaño dado.
  TextStyle display(double size, {Color? color, FontWeight? weight}) =>
      TextStyle(
        fontFamily: displayFamily,
        fontWeight: weight ?? displayWeight,
        fontSize: size,
        height: displayHeight,
        letterSpacing: size * displayTracking,
        color: color ?? ink,
      );

  /// Texto de display en mayúsculas si el estilo lo pide (Escenario).
  String displayCase(String value) =>
      displayUppercase ? value.toUpperCase() : value;

  @override
  GesbandTokens copyWith() => this;

  @override
  GesbandTokens lerp(GesbandTokens? other, double t) =>
      other == null || t < 0.5 ? this : other;
}

extension on Color {
  /// Tinta oscura de la paleta para usar sobre colores claros.
  Color get darkest =>
      relativeLuminance(this) < 0.2 ? this : const Color(0xFF111214);
}
