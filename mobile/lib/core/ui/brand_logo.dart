import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../localization/app_strings.dart';
import '../theme/brand.dart';
import '../theme/color_contrast.dart';
import '../theme/gesband_tokens.dart';
import '../theme/visual_style.dart';

/// Logotipo de una banda recortado con esquinas redondeadas o, si no tiene,
/// monograma con sus iniciales sobre su color principal.
///
/// Muchos logotipos son monocromos y cuadrados (p. ej. una lira blanca sobre
/// negro): el recorte redondeado los integra sin añadirles un marco.
class BrandLogo extends StatelessWidget {
  const BrandLogo({
    super.key,
    required this.name,
    this.logo,
    this.size = 40,
    this.color,
    this.inverted = false,
  });

  /// Logo de la marca activa del tema.
  factory BrandLogo.of(Brand brand, {Key? key, double size = 40}) => BrandLogo(
        key: key,
        name: brand.name,
        logo: brand.logo,
        size: size,
      );

  final String name;
  final Uint8List? logo;
  final double size;

  /// Color de fondo del monograma; por defecto, el principal de la marca.
  final Color? color;

  /// Monograma claro sobre fondo de color (cabecera de Festa).
  final bool inverted;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final strings = AppStrings.of(context);
    final radius = switch (t.style) {
      VisualStyle.escenario => size * 0.25,
      VisualStyle.partitura => size * 0.5,
      VisualStyle.festa => size * 0.34,
    };
    final bytes = logo;
    final Widget content;
    if (bytes != null) {
      content = Image.memory(
        bytes,
        width: size,
        height: size,
        fit: BoxFit.cover,
        gaplessPlayback: true,
        errorBuilder: (_, __, ___) => _monogram(t, radius),
      );
    } else {
      content = _monogram(t, radius);
    }
    final clip = BorderRadius.circular(bytes == null ? radius : size * 0.22);
    // Un logotipo o monograma del color de la banda puede fundirse con el
    // fondo (negro sobre oscuro): lleva el borde de las superficies de marca.
    // Con un color ajeno (otra banda en el selector) se desconoce su
    // secundario: si se funde, se usa la línea del tema.
    final edge = inverted
        ? null
        : color == null
            ? t.primaryEdge
            : primaryEdgeFor(
                primary: color!,
                secondary: color!,
                background: t.background,
                surface: t.surface,
                line: t.line,
              );
    return Semantics(
      label: strings.logoOf(name),
      image: true,
      child: ExcludeSemantics(
        child: Container(
          key: const Key('brand-logo'),
          foregroundDecoration: edge == null
              ? null
              : BoxDecoration(
                  borderRadius: clip,
                  border: Border.all(
                      color: edge, width: GesbandTokens.primaryEdgeWidth),
                ),
          child: ClipRRect(
            borderRadius: clip,
            child: SizedBox.square(dimension: size, child: content),
          ),
        ),
      ),
    );
  }

  Widget _monogram(GesbandTokens t, double radius) {
    final background = inverted ? t.onPrimary : (color ?? t.primary);
    final ink = inverted ? t.primaryOnInk : readableInk(background);
    return ColoredBox(
      color: background,
      child: Center(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          child: Padding(
            padding: EdgeInsets.all(size * 0.12),
            child: Text(
              monogramOf(name),
              textScaler: TextScaler.noScaling,
              style:
                  t.display(size * 0.42, color: ink, weight: FontWeight.w700),
            ),
          ),
        ),
      ),
    );
  }
}
