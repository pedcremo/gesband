import 'package:flutter/material.dart';

import '../theme/brand.dart';
import '../theme/gesband_tokens.dart';
import '../theme/visual_style.dart';
import 'brand_logo.dart';
import 'components.dart';

/// Cabecera de las secciones principales con la marca de la banda.
///
/// - Escenario: logotipo cuadrado y nombre condensado en mayúsculas.
/// - Partitura: monograma circular con anillo secundario, lema en cursiva y
///   pentagrama.
/// - Festa: bloque del color principal con la «faja» diagonal del secundario.
///
/// [title] es el nombre de la sección; en Festa se muestra dentro del bloque.
class BrandHeader extends StatelessWidget {
  const BrandHeader({
    super.key,
    required this.brand,
    this.title,
    this.trailing,
  });

  final Brand brand;
  final String? title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return switch (t.style) {
      VisualStyle.escenario => _escenario(context, t),
      VisualStyle.partitura => _partitura(context, t),
      VisualStyle.festa => _festa(context, t),
    };
  }

  Widget _escenario(BuildContext context, GesbandTokens t) => SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(GesbandSpacing.xl,
              GesbandSpacing.lg, GesbandSpacing.xl, GesbandSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  BrandLogo(name: brand.name, logo: brand.logo, size: 40),
                  const SizedBox(width: GesbandSpacing.md),
                  Expanded(child: _nameAndMotto(context, t, 20)),
                  if (trailing != null) trailing!,
                ],
              ),
              if (title != null) ...[
                const SizedBox(height: GesbandSpacing.xl),
                Semantics(header: true, child: DisplayText(title!, size: 34)),
              ],
            ],
          ),
        ),
      );

  Widget _partitura(BuildContext context, GesbandTokens t) => SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(GesbandSpacing.xxl,
              GesbandSpacing.lg, GesbandSpacing.xxl, GesbandSpacing.sm),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(1),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: t.secondary, width: 1),
                    ),
                    child: Container(
                      padding: const EdgeInsets.all(3),
                      decoration: BoxDecoration(
                          shape: BoxShape.circle, color: t.background),
                      child: BrandLogo(
                          name: brand.name, logo: brand.logo, size: 44),
                    ),
                  ),
                  const SizedBox(width: GesbandSpacing.md),
                  Expanded(child: _nameAndMotto(context, t, 19)),
                  if (trailing != null) trailing!,
                ],
              ),
              const SizedBox(height: GesbandSpacing.lg),
              const StaffDivider(),
              if (title != null) ...[
                const SizedBox(height: GesbandSpacing.lg),
                Semantics(header: true, child: DisplayText(title!, size: 30)),
              ],
            ],
          ),
        ),
      );

  Widget _festa(BuildContext context, GesbandTokens t) {
    final textTheme = Theme.of(context).textTheme;
    return ClipRect(
      child: ColoredBox(
        color: t.primary,
        child: Stack(
          children: [
            // La faja: dos bandas diagonales del color secundario.
            Positioned(
              left: -40,
              right: -40,
              bottom: 18,
              child: ExcludeSemantics(
                child: Transform.rotate(
                  angle: -0.105,
                  child: Container(height: 22, color: t.secondary),
                ),
              ),
            ),
            Positioned(
              left: -40,
              right: -40,
              bottom: 6,
              child: ExcludeSemantics(
                child: Transform.rotate(
                  angle: -0.105,
                  child: Container(
                    height: 6,
                    color: t.secondary.withValues(alpha: 0.6),
                  ),
                ),
              ),
            ),
            SafeArea(
              bottom: false,
              child: Padding(
                padding:
                    const EdgeInsets.fromLTRB(22, GesbandSpacing.lg, 22, 52),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        BrandLogo(
                          name: brand.name,
                          logo: brand.logo,
                          size: 46,
                          inverted: true,
                        ),
                        const SizedBox(width: GesbandSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              DisplayText(brand.name,
                                  size: 19, color: t.onPrimary, maxLines: 2),
                              if (brand.motto != null)
                                Text(
                                  brand.motto!,
                                  style: textTheme.bodySmall!
                                      .copyWith(color: t.onPrimary),
                                ),
                            ],
                          ),
                        ),
                        if (trailing != null) trailing!,
                      ],
                    ),
                    if (title != null) ...[
                      const SizedBox(height: GesbandSpacing.lg),
                      Semantics(
                        header: true,
                        child:
                            DisplayText(title!, size: 28, color: t.onPrimary),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _nameAndMotto(BuildContext context, GesbandTokens t, double size) {
    final textTheme = Theme.of(context).textTheme;
    final partitura = t.style == VisualStyle.partitura;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DisplayText(
          brand.name,
          size: size,
          maxLines: 2,
          weight: partitura ? FontWeight.w700 : null,
        ),
        if (brand.motto != null)
          Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Text(
              brand.motto!,
              style: textTheme.bodySmall!.copyWith(
                fontFamily: partitura ? t.displayFamily : null,
                fontStyle: partitura ? FontStyle.italic : null,
              ),
            ),
          ),
      ],
    );
  }
}
