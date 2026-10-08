import 'package:flutter/material.dart';

import '../localization/app_strings.dart';
import '../theme/gesband_tokens.dart';
import '../theme/visual_style.dart';

/// Tono semántico de una píldora o aviso.
enum Tone { success, warning, danger, neutral, brand }

({Color background, Color ink}) toneColors(GesbandTokens t, Tone tone) =>
    switch (tone) {
      Tone.success => (background: t.success, ink: t.successInk),
      Tone.warning => (background: t.warning, ink: t.warningInk),
      Tone.danger => (background: t.danger, ink: t.dangerInk),
      Tone.neutral => (background: t.surfaceMuted, ink: t.ink),
      Tone.brand => (background: t.primaryTint, ink: t.onPrimaryTint),
    };

/// Píldora de estado: «Asistiré», «Responde», «No podré»...
class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, required this.tone});

  final String label;
  final Tone tone;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final colors = toneColors(t, tone);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style:
            Theme.of(context).textTheme.labelSmall!.copyWith(color: colors.ink),
      ),
    );
  }
}

/// Texto con la tipografía de display del estilo, en mayúsculas si toca.
class DisplayText extends StatelessWidget {
  const DisplayText(
    this.text, {
    super.key,
    required this.size,
    this.color,
    this.maxLines,
    this.weight,
    this.textAlign,
  });

  final String text;
  final double size;
  final Color? color;
  final int? maxLines;
  final FontWeight? weight;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final shown = t.displayCase(text);
    final widget = Text(
      shown,
      maxLines: maxLines,
      overflow: maxLines == null ? null : TextOverflow.ellipsis,
      textAlign: textAlign,
      style: t.display(size, color: color, weight: weight),
    );
    // Las mayúsculas son solo visuales: el lector de pantalla recibe el
    // texto original, que no deletrea como siglas.
    return shown == text
        ? widget
        : Semantics(label: text, excludeSemantics: true, child: widget);
  }
}

/// Separador de pentagrama de Partitura: cinco líneas, la central del color
/// de la banda.
class StaffDivider extends StatelessWidget {
  const StaffDivider({super.key});

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return ExcludeSemantics(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < 5; i++) ...[
            if (i > 0) const SizedBox(height: 3),
            Container(height: 1, color: i == 2 ? t.primaryText : t.staff),
          ],
        ],
      ),
    );
  }
}

/// Título de sección: en Escenario, display apagado en mayúsculas; en
/// Partitura, serif; en Festa, display corto.
class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return Semantics(
      header: true,
      child: switch (t.style) {
        VisualStyle.escenario => DisplayText(text, size: 22, color: t.muted),
        VisualStyle.partitura => DisplayText(text, size: 22),
        VisualStyle.festa => DisplayText(text, size: 20),
      },
    );
  }
}

/// Etiqueta pequeña en versalitas espaciadas («PRÓXIMA CONVOCATORIA»).
class Eyebrow extends StatelessWidget {
  const Eyebrow(this.text, {super.key, this.color});

  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return Text(
      text.toUpperCase(),
      style: Theme.of(context).textTheme.labelSmall!.copyWith(
            color: color ?? t.muted,
            letterSpacing: 1.6,
          ),
    );
  }
}

/// Superficie de tarjeta del estilo activo. En Partitura lleva filete; en
/// Festa, sombra suave.
class SurfaceCard extends StatelessWidget {
  const SurfaceCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(GesbandSpacing.lg),
    this.onTap,
    this.borderColor,
    this.color,
    this.semanticLabel,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;

  /// Borde que llama la atención (p. ej. una respuesta pendiente).
  final Color? borderColor;
  final Color? color;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final radius = BorderRadius.circular(t.radiusCard);
    final side = borderColor != null
        ? BorderSide(color: borderColor!, width: 2)
        : t.style == VisualStyle.partitura
            ? BorderSide(color: t.line)
            : BorderSide.none;
    final shadows = t.style == VisualStyle.festa && !t.isDark
        ? [
            BoxShadow(
              color: t.shadow,
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
            BoxShadow(
              color: t.shadow,
              blurRadius: 24,
              offset: const Offset(0, 8),
            ),
          ]
        : const <BoxShadow>[];
    final content = Padding(padding: padding, child: child);
    return Semantics(
      label: semanticLabel,
      button: onTap != null,
      container: true,
      child: DecoratedBox(
        decoration: BoxDecoration(borderRadius: radius, boxShadow: shadows),
        child: Material(
          color: color ?? t.surface,
          shape: RoundedRectangleBorder(borderRadius: radius, side: side),
          clipBehavior: Clip.antiAlias,
          child:
              onTap == null ? content : InkWell(onTap: onTap, child: content),
        ),
      ),
    );
  }
}

/// Indicador de carga centrado y anunciado.
class LoadingView extends StatelessWidget {
  const LoadingView({super.key});

  @override
  Widget build(BuildContext context) => Center(
        child: Semantics(
          label: AppStrings.of(context).loading,
          child: const CircularProgressIndicator(),
        ),
      );
}

/// Estado vacío o de error: icono, mensaje y, si procede, una acción.
class MessageView extends StatelessWidget {
  const MessageView({
    super.key,
    required this.icon,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.tone = Tone.neutral,
  });

  final IconData icon;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final Tone tone;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final colors = toneColors(t, tone);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(GesbandSpacing.xxl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: colors.background,
                borderRadius: BorderRadius.circular(t.radiusCard),
              ),
              child: Icon(icon, size: 32, color: colors.ink),
            ),
            const SizedBox(height: GesbandSpacing.lg),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: GesbandSpacing.lg),
              OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

/// Aviso en línea con icono, texto y acción opcional (sin conexión, avisos
/// pendientes, plazo cerrado...).
class InlineNotice extends StatelessWidget {
  const InlineNotice({
    super.key,
    required this.icon,
    required this.message,
    this.tone = Tone.warning,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String message;
  final Tone tone;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final colors = toneColors(t, tone);
    final text = Theme.of(context).textTheme.bodyMedium!;
    return Container(
      padding: const EdgeInsets.fromLTRB(GesbandSpacing.lg, GesbandSpacing.md,
          GesbandSpacing.sm, GesbandSpacing.md),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(t.radiusSmall.clamp(8, 16)),
      ),
      child: Row(
        children: [
          Icon(icon, color: colors.ink, size: 22),
          const SizedBox(width: GesbandSpacing.md),
          Expanded(
            child: Text(message, style: text.copyWith(color: colors.ink)),
          ),
          if (actionLabel != null && onAction != null)
            TextButton(
              style: TextButton.styleFrom(foregroundColor: colors.ink),
              onPressed: onAction,
              child: Text(actionLabel!),
            ),
        ],
      ),
    );
  }
}

/// Barra superior de las pantallas que se abren encima de la navegación:
/// botón de volver de 48 dp y título con la tipografía del estilo.
class ScreenBar extends StatelessWidget implements PreferredSizeWidget {
  const ScreenBar({super.key, required this.title, this.actions = const []});

  final String title;
  final List<Widget> actions;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final canPop = Navigator.of(context).canPop();
    return AppBar(
      toolbarHeight: 64,
      automaticallyImplyLeading: false,
      leading: canPop
          ? IconButton(
              tooltip: AppStrings.of(context).back,
              icon: const Icon(Icons.arrow_back),
              onPressed: () => Navigator.of(context).maybePop(),
            )
          : null,
      titleSpacing: canPop ? 0 : GesbandSpacing.xl,
      title: Semantics(
        header: true,
        child: Text(t.displayCase(title),
            maxLines: 1, overflow: TextOverflow.ellipsis),
      ),
      actions: actions,
      bottom: t.style == VisualStyle.partitura
          ? PreferredSize(
              preferredSize: const Size.fromHeight(1),
              child: Container(height: 1, color: t.line),
            )
          : null,
    );
  }
}

/// Selector de opciones en fila con dianas de 48 dp (modo de color, idioma).
class ChoiceSegments<T> extends StatelessWidget {
  const ChoiceSegments({
    super.key,
    required this.options,
    required this.selected,
    required this.onSelected,
  });

  final List<(T, String)> options;
  final T selected;
  final ValueChanged<T> onSelected;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final label = Theme.of(context).textTheme.labelMedium!;
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: t.surfaceMuted,
        borderRadius: BorderRadius.circular(t.radiusButton.clamp(0, 18) + 4),
      ),
      child: Row(
        children: [
          for (final (value, text) in options)
            Expanded(
              child: Semantics(
                selected: value == selected,
                button: true,
                inMutuallyExclusiveGroup: true,
                child: Material(
                  key: ValueKey('choice-$value'),
                  color: value == selected ? t.primary : Colors.transparent,
                  shape: RoundedRectangleBorder(
                    borderRadius:
                        BorderRadius.circular(t.radiusButton.clamp(0, 18)),
                    side:
                        value == selected ? t.primaryEdgeSide : BorderSide.none,
                  ),
                  child: InkWell(
                    borderRadius:
                        BorderRadius.circular(t.radiusButton.clamp(0, 18)),
                    onTap: () => onSelected(value),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(
                          minHeight: GesbandSpacing.minTarget),
                      child: Center(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 8),
                          child: Text(
                            text,
                            textAlign: TextAlign.center,
                            style: label.copyWith(
                              color: value == selected ? t.onPrimary : t.ink,
                              fontWeight: value == selected
                                  ? FontWeight.w700
                                  : FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
