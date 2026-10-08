import 'package:flutter/material.dart';

import '../localization/app_strings.dart';
import '../theme/gesband_tokens.dart';
import '../theme/visual_style.dart';

class SectionNavItem {
  const SectionNavItem({
    required this.key,
    required this.icon,
    required this.label,
    this.badge = false,
  });

  final Key key;
  final IconData icon;
  final String label;

  /// Punto de aviso (p. ej. avisos sin leer).
  final bool badge;
}

/// Navegación inferior entre secciones.
///
/// - Escenario: cápsula flotante; el elemento activo, relleno del principal.
/// - Partitura: barra con filete superior; el activo, en el color de texto
///   de la banda.
/// - Festa: barra redondeada arriba; el activo, con píldora teñida.
class SectionNav extends StatelessWidget {
  const SectionNav({
    super.key,
    required this.items,
    required this.selected,
    required this.onSelected,
  });

  final List<SectionNavItem> items;
  final int selected;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final row = Row(
      children: [
        for (var i = 0; i < items.length; i++)
          Expanded(child: _item(context, t, items[i], i == selected, i)),
      ],
    );
    final semantics = AppStrings.of(context).sections;
    return Semantics(
      container: true,
      label: semantics,
      explicitChildNodes: true,
      child: switch (t.style) {
        VisualStyle.escenario => SafeArea(
            top: false,
            minimum: const EdgeInsets.only(bottom: GesbandSpacing.lg),
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: GesbandSpacing.lg),
              child: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: t.surface,
                  borderRadius: BorderRadius.circular(t.radiusNav),
                  border: t.isDark ? null : Border.all(color: t.line),
                ),
                child: row,
              ),
            ),
          ),
        VisualStyle.partitura => DecoratedBox(
            decoration: BoxDecoration(
              color: t.surface,
              border: Border(top: BorderSide(color: t.line)),
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.all(GesbandSpacing.sm),
                child: row,
              ),
            ),
          ),
        VisualStyle.festa => DecoratedBox(
            decoration: BoxDecoration(
              color: t.surface,
              borderRadius:
                  BorderRadius.vertical(top: Radius.circular(t.radiusNav)),
              border: t.isDark ? Border(top: BorderSide(color: t.line)) : null,
              boxShadow: t.isDark
                  ? null
                  : [
                      BoxShadow(
                        color: t.shadow,
                        blurRadius: 20,
                        offset: const Offset(0, -4),
                      ),
                    ],
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                    10, GesbandSpacing.sm, 10, GesbandSpacing.sm),
                child: row,
              ),
            ),
          ),
      },
    );
  }

  Widget _item(BuildContext context, GesbandTokens t, SectionNavItem item,
      bool active, int index) {
    final label = Theme.of(context).textTheme.labelSmall!;
    final Color foreground;
    final Color? fill;
    switch (t.style) {
      case VisualStyle.escenario:
        foreground = active ? t.onPrimary : t.muted;
        fill = active ? t.primary : null;
      case VisualStyle.partitura:
        foreground = active ? t.primaryText : t.muted;
        fill = null;
      case VisualStyle.festa:
        foreground = active ? t.onPrimaryTint : t.muted;
        fill = null;
    }
    Widget icon = Icon(item.icon, size: 22, color: foreground);
    if (t.style == VisualStyle.festa) {
      icon = AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width: 56,
        height: 30,
        decoration: BoxDecoration(
          color: active ? t.primaryTint : Colors.transparent,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Center(child: icon),
      );
    }
    if (item.badge) {
      icon = Badge(
        smallSize: 8,
        backgroundColor: t.style == VisualStyle.escenario && active
            ? t.onPrimary
            : t.primaryText,
        child: icon,
      );
    }
    final radius = BorderRadius.circular(
        t.style == VisualStyle.escenario ? 16 : t.radiusSmall);
    return Semantics(
      selected: active,
      button: true,
      child: Material(
        key: item.key,
        color: fill ?? Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: radius,
          side: fill != null ? t.primaryEdgeSide : BorderSide.none,
        ),
        child: InkWell(
          borderRadius: radius,
          onTap: () => onSelected(index),
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 52),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  icon,
                  const SizedBox(height: 2),
                  Text(
                    item.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: label.copyWith(
                      color: foreground,
                      fontWeight: active ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
