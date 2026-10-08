import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/painting.dart';

import '../models/models.dart';
import 'color_contrast.dart';
import 'visual_style.dart';

/// Marca con la que se viste la app: la de la asociación activa o, si no hay
/// ninguna, la de Gesband.
class Brand {
  const Brand({
    required this.name,
    required this.primary,
    required this.secondary,
    this.associationId,
    this.motto,
    this.style = VisualStyle.escenario,
    this.colorMode = BandColorMode.system,
    this.logo,
  });

  factory Brand.fromAssociation(Association association, {Uint8List? logo}) =>
      Brand(
        associationId: association.id,
        name: association.name,
        motto: association.motto,
        primary: parseHexColor(association.primaryColor) ?? gesband.primary,
        secondary:
            parseHexColor(association.secondaryColor) ?? gesband.secondary,
        style: association.visualStyle,
        colorMode: association.colorMode,
        logo: logo,
      );

  /// Marca neutra de Gesband, con el estilo Escenario.
  static const gesband = Brand(
    name: 'Gesband',
    primary: Color(0xFF7A1F2B),
    secondary: Color(0xFFC9A227),
  );

  /// Logotipos de hasta este tamaño se guardan para la pantalla de acceso,
  /// igual que en el cliente web (decisión 0005).
  static const maxStoredLogoBytes = 120 * 1024;

  final String? associationId;
  final String name;
  final String? motto;
  final Color primary;
  final Color secondary;
  final VisualStyle style;
  final BandColorMode colorMode;
  final Uint8List? logo;

  bool get isGesband => associationId == null;

  /// Iniciales para el monograma cuando no hay logotipo. Se saltan las
  /// palabras de enlace para que «Unió Musical de Bocairent» sea «UM».
  String get initials => monogramOf(name);

  Brand withLogo(Uint8List? value) => Brand(
        associationId: associationId,
        name: name,
        motto: motto,
        primary: primary,
        secondary: secondary,
        style: style,
        colorMode: colorMode,
        logo: value,
      );

  Map<String, Object?> toJson() => {
        'association_id': associationId,
        'name': name,
        'motto': motto,
        'primary_color': toHexColor(primary),
        'secondary_color': toHexColor(secondary),
        'visual_style': style.name,
        'color_mode': colorMode.name,
        if (logo != null && logo!.length <= maxStoredLogoBytes)
          'logo': base64Encode(logo!),
      };

  String toStoredJson() => jsonEncode(toJson());

  /// Lee la marca guardada; si está dañada devuelve `null` y se usa Gesband.
  static Brand? fromStoredJson(String? value) {
    if (value == null) return null;
    try {
      final json = jsonDecode(value) as Map<String, dynamic>;
      final logo = json['logo'] as String?;
      return Brand(
        associationId: json['association_id'] as String?,
        name: json['name'] as String? ?? gesband.name,
        motto: json['motto'] as String?,
        primary:
            parseHexColor(json['primary_color'] as String?) ?? gesband.primary,
        secondary: parseHexColor(json['secondary_color'] as String?) ??
            gesband.secondary,
        style: VisualStyle.fromWire(json['visual_style']),
        colorMode: BandColorMode.fromWire(json['color_mode']),
        logo: logo == null ? null : base64Decode(logo),
      );
    } catch (_) {
      return null;
    }
  }
}

const _linkWords = {
  'de',
  'del',
  'la',
  'las',
  'los',
  'el',
  'i',
  'y',
  'and',
  'of',
  'the',
  'dels',
  'les',
  'l',
  'd',
};

/// Hasta dos iniciales significativas de un nombre.
String monogramOf(String name) {
  final words = name
      .split(RegExp(r"[\s'’\-]+"))
      .where((word) => word.isNotEmpty)
      .toList();
  final meaningful =
      words.where((word) => !_linkWords.contains(word.toLowerCase())).toList();
  final source = meaningful.isEmpty ? words : meaningful;
  if (source.isEmpty) return '?';
  return source
      .take(2)
      .map((word) => String.fromCharCode(word.runes.first).toUpperCase())
      .join();
}
