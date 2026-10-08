import 'dart:math' as math;
import 'dart:ui';

/// Contraste mínimo de WCAG 2.1 AA para texto normal.
const double minimumTextContrast = 4.5;

/// Lee `#RGB` o `#RRGGBB` (con o sin almohadilla). Devuelve `null` si el
/// valor no es un color válido.
Color? parseHexColor(String? value) {
  if (value == null) return null;
  var hex = value.trim();
  if (hex.startsWith('#')) hex = hex.substring(1);
  if (hex.length == 3) hex = hex.split('').map((c) => '$c$c').join();
  if (hex.length != 6) return null;
  final parsed = int.tryParse(hex, radix: 16);
  return parsed == null ? null : Color(0xFF000000 | parsed);
}

/// `#RRGGBB` en mayúsculas, para guardar y comparar.
String toHexColor(Color color) {
  int channel(double value) => (value * 255).round().clamp(0, 255);
  return '#${[
    channel(color.r),
    channel(color.g),
    channel(color.b),
  ].map((v) => v.toRadixString(16).padLeft(2, '0')).join().toUpperCase()}';
}

/// Luminancia relativa de WCAG 2.1. Ignora la transparencia.
double relativeLuminance(Color color) {
  double linear(double channel) => channel <= 0.03928
      ? channel / 12.92
      : math.pow((channel + 0.055) / 1.055, 2.4).toDouble();
  return 0.2126 * linear(color.r) +
      0.7152 * linear(color.g) +
      0.0722 * linear(color.b);
}

/// Relación de contraste entre dos colores opacos, de 1 a 21.
double contrastRatio(Color a, Color b) {
  final x = relativeLuminance(a);
  final y = relativeLuminance(b);
  return (math.max(x, y) + 0.05) / (math.min(x, y) + 0.05);
}

/// Tinta legible encima de [background]: la de [dark] o [light] que más
/// contraste. Si ninguna llega a 4.5:1 (grises medios), negro o blanco puros,
/// que siempre lo alcanzan.
Color readableInk(
  Color background, {
  Color dark = const Color(0xFF111214),
  Color light = const Color(0xFFFFFFFF),
}) {
  Color best(Color a, Color b) =>
      contrastRatio(a, background) >= contrastRatio(b, background) ? a : b;
  final ink = best(dark, light);
  if (contrastRatio(ink, background) >= minimumTextContrast) return ink;
  return best(const Color(0xFF000000), const Color(0xFFFFFFFF));
}

/// Versión de [color] apta para texto sobre [background].
///
/// Si ya alcanza [minimum], se usa tal cual. Si no, se acerca a negro (sobre
/// fondos claros) o a blanco (sobre oscuros) hasta alcanzarlo, conservando el
/// tono. El color de la banda nunca llega sin comprobar al texto
/// (decisión 0005).
Color legibleOn(
  Color color,
  Color background, {
  double minimum = minimumTextContrast,
}) {
  final opaque = color.withValues(alpha: 1);
  if (contrastRatio(opaque, background) >= minimum) return opaque;
  final target = relativeLuminance(background) > 0.18
      ? const Color(0xFF000000)
      : const Color(0xFFFFFFFF);
  for (var step = 1; step <= 20; step++) {
    final candidate = Color.lerp(opaque, target, step / 20)!;
    if (contrastRatio(candidate, background) >= minimum) return candidate;
  }
  return target;
}
