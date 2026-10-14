import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/models.dart';

/// Formatos de fecha del idioma activo. Los datos de `intl` los carga
/// `GlobalMaterialLocalizations` para los tres idiomas de la app.
class DateLabels {
  DateLabels.of(BuildContext context)
      : _tag = Localizations.localeOf(context).languageCode,
        _material = MaterialLocalizations.of(context),
        _use24h = MediaQuery.maybeAlwaysUse24HourFormatOf(context) ?? false;

  final String _tag;
  final MaterialLocalizations _material;
  final bool _use24h;

  static String _clean(String value) => value.replaceAll('.', '').trim();

  static String _capitalized(String value) =>
      value.isEmpty ? value : value[0].toUpperCase() + value.substring(1);

  /// «jue»
  String weekdayShort(DateTime date) => _clean(DateFormat.E(_tag).format(date));

  /// «nov»
  String monthShort(DateTime date) => _clean(DateFormat.MMM(_tag).format(date));

  /// «Noviembre», o «Noviembre 2027» si no es del año en curso.
  String monthTitle(DateTime date, DateTime now) {
    final month = _capitalized(DateFormat.LLLL(_tag).format(date));
    return date.year == now.year ? month : '$month ${date.year}';
  }

  /// «sábado 22 nov»
  String longDay(DateTime date) =>
      '${DateFormat.EEEE(_tag).format(date)} ${date.day} ${monthShort(date)}';

  /// «18:45»
  String time(DateTime date) => _material.formatTimeOfDay(
        TimeOfDay.fromDateTime(date),
        alwaysUse24HourFormat: _use24h,
      );

  /// «22 nov 2026», siempre con el año.
  String mediumDate(DateTime date) =>
      _clean(DateFormat.yMMMd(_tag).format(date));

  /// «22 nov 2026 · 18:45», como hasta ahora en el detalle.
  String dateTime(DateTime date) =>
      '${_material.formatMediumDate(date)} · ${time(date)}';
}

/// Importes en el formato del idioma activo: «25,00 €» en castellano y
/// valenciano, «€25.00» en inglés.
class MoneyLabels {
  MoneyLabels.of(BuildContext context)
      : _tag = Localizations.localeOf(context).languageCode;

  MoneyLabels.forLanguage(String languageCode) : _tag = languageCode;

  final String _tag;

  /// La división solo sirve para dibujar: el importe ya llega exacto en
  /// céntimos y nunca se suma en coma flotante.
  String format(Money value) => NumberFormat.simpleCurrency(
        locale: _tag,
        name: value.currency,
        decimalDigits: 2,
      ).format(value.cents / 100);
}
