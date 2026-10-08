import 'package:flutter/material.dart';

import 'brand.dart';
import 'color_contrast.dart';
import 'gesband_tokens.dart';

/// Genera el `ThemeData` de Material a partir de los tokens, para que los
/// componentes estándar (botones, campos, diálogos, avisos) hereden el
/// estilo sin colores escritos en cada pantalla.
ThemeData buildGesbandTheme(Brand brand, Brightness brightness) {
  final t = GesbandTokens.resolve(brand, brightness);

  // `primary` del esquema es la versión legible sobre el fondo: Material lo
  // usa para texto e iconos. El color de la banda tal cual solo pinta fondos
  // (botones rellenos, cartel), que se configuran aparte.
  final scheme = ColorScheme(
    brightness: brightness,
    primary: t.primaryText,
    onPrimary: t.isDark ? t.background : t.surface,
    primaryContainer: t.primaryTint,
    onPrimaryContainer: t.onPrimaryTint,
    secondary: t.secondary,
    onSecondary: t.onSecondary,
    secondaryContainer: t.surfaceMuted,
    onSecondaryContainer: t.ink,
    tertiary: t.highlight,
    onTertiary: t.surface,
    error: t.dangerInk,
    onError: t.danger,
    errorContainer: t.danger,
    onErrorContainer: t.dangerInk,
    surface: t.surface,
    onSurface: t.ink,
    onSurfaceVariant: t.muted,
    surfaceContainerLowest: t.background,
    surfaceContainerLow: t.surface,
    surfaceContainer: t.surface,
    surfaceContainerHigh: t.surface,
    surfaceContainerHighest: t.surfaceMuted,
    outline: t.muted,
    outlineVariant: t.line,
    inverseSurface: t.ink,
    onInverseSurface: t.background,
    inversePrimary: t.primaryOnInk,
    shadow: const Color(0xFF000000),
    scrim: const Color(0xFF000000),
  );

  TextStyle body(double size, FontWeight weight, {double height = 1.35}) =>
      TextStyle(
        fontFamily: t.bodyFamily,
        fontSize: size,
        fontWeight: weight,
        height: height,
        color: t.ink,
      );

  final textTheme = TextTheme(
    displayLarge: t.display(56),
    displayMedium: t.display(44),
    displaySmall: t.display(36),
    headlineLarge: t.display(32),
    headlineMedium: t.display(28),
    headlineSmall: t.display(24),
    titleLarge: t.display(22),
    titleMedium: body(16, FontWeight.w600),
    titleSmall: body(14, FontWeight.w600),
    bodyLarge: body(16, FontWeight.w400),
    bodyMedium: body(15, FontWeight.w400),
    bodySmall: body(13, FontWeight.w400).copyWith(color: t.muted),
    labelLarge: body(15, FontWeight.w700, height: 1.2),
    labelMedium: body(13, FontWeight.w600, height: 1.2),
    labelSmall: body(12, FontWeight.w700, height: 1.2),
  );

  final buttonShape = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(t.radiusButton),
  );
  const buttonSize = Size(64, GesbandSpacing.minTarget);
  final buttonPadding = const EdgeInsets.symmetric(
    horizontal: GesbandSpacing.xl,
    vertical: GesbandSpacing.md,
  );

  OutlineInputBorder inputBorder(Color color, [double width = 1]) =>
      OutlineInputBorder(
        borderRadius: BorderRadius.circular(t.radiusButton.clamp(0, 16)),
        borderSide: BorderSide(color: color, width: width),
      );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme,
    fontFamily: t.bodyFamily,
    textTheme: textTheme,
    scaffoldBackgroundColor: t.background,
    canvasColor: t.background,
    dividerColor: t.line,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    visualDensity: VisualDensity.standard,
    extensions: [t],
    appBarTheme: AppBarTheme(
      backgroundColor: t.background,
      foregroundColor: t.ink,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: t.display(22),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: t.primary,
        foregroundColor: t.onPrimary,
        disabledBackgroundColor: t.surfaceMuted,
        disabledForegroundColor: t.muted,
        minimumSize: buttonSize,
        padding: buttonPadding,
        shape: buttonShape,
        // Banda de color casi igual al fondo: el botón lleva borde.
        side: t.primaryEdge == null ? null : t.primaryEdgeSide,
        textStyle: textTheme.labelLarge,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: t.ink,
        disabledForegroundColor: t.muted,
        minimumSize: buttonSize,
        padding: buttonPadding,
        shape: buttonShape,
        side: BorderSide(color: t.isDark ? t.muted : t.staff, width: 1.5),
        textStyle: textTheme.labelLarge,
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: t.primaryText,
        minimumSize: buttonSize,
        padding: const EdgeInsets.symmetric(horizontal: GesbandSpacing.lg),
        shape: buttonShape,
        textStyle: textTheme.labelLarge,
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(
        foregroundColor: t.ink,
        minimumSize: const Size.square(GesbandSpacing.minTarget),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: t.surface,
      labelStyle: body(15, FontWeight.w500).copyWith(color: t.muted),
      floatingLabelStyle: body(15, FontWeight.w600).copyWith(color: t.ink),
      helperStyle: textTheme.bodySmall,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: GesbandSpacing.lg,
        vertical: GesbandSpacing.lg,
      ),
      border: inputBorder(t.line),
      enabledBorder: inputBorder(t.line),
      focusedBorder: inputBorder(t.primaryText, 2),
      errorBorder: inputBorder(t.dangerInk),
      focusedErrorBorder: inputBorder(t.dangerInk, 2),
    ),
    cardTheme: CardThemeData(
      color: t.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(t.radiusCard),
      ),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: t.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(t.radiusLarge),
      ),
      titleTextStyle: t.display(24),
      contentTextStyle: textTheme.bodyMedium,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: t.ink,
      contentTextStyle: body(15, FontWeight.w500).copyWith(color: t.background),
      // El aviso usa la tinta del tema como fondo: la acción se corrige
      // contra ella.
      actionTextColor: legibleOn(t.primary, t.ink),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(t.radiusButton.clamp(0, 16)),
      ),
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: t.surface,
      surfaceTintColor: Colors.transparent,
      textStyle: textTheme.bodyMedium,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(t.radiusSmall),
      ),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: t.primaryText,
      linearTrackColor: t.surfaceMuted,
      circularTrackColor: Colors.transparent,
    ),
    radioTheme: RadioThemeData(
      fillColor: WidgetStateProperty.resolveWith(
        (states) =>
            states.contains(WidgetState.selected) ? t.primaryText : t.muted,
      ),
    ),
    dividerTheme: DividerThemeData(color: t.line, thickness: 1, space: 1),
    listTileTheme: ListTileThemeData(
      iconColor: t.muted,
      textColor: t.ink,
      minVerticalPadding: GesbandSpacing.md,
    ),
    bottomSheetTheme: BottomSheetThemeData(
      backgroundColor: t.surface,
      surfaceTintColor: Colors.transparent,
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: t.ink,
        borderRadius: BorderRadius.circular(t.radiusSmall),
      ),
      textStyle: body(13, FontWeight.w500).copyWith(color: t.background),
    ),
  );
}
