import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';
import 'app_theme.dart';
import 'brand.dart';
import 'visual_style.dart';

/// Descarga un archivo protegido del API (logotipo, foto). Devuelve `null`
/// si no existe o no se puede obtener.
typedef ProtectedImageLoader = Future<Uint8List?> Function(String url);

/// Marca activa, modo de color y temas resultantes.
///
/// Antes de elegir banda (y en el acceso) se usa la marca de la última
/// asociación guardada en el dispositivo; si no hay ninguna, Gesband con
/// Escenario. Al elegir banda se viste con la suya y se guarda.
class ThemeController extends ChangeNotifier {
  ThemeController(this._preferences, {ProtectedImageLoader? loadImage})
      : _loadImage = loadImage,
        _brand = Brand.fromStoredJson(_preferences.getString(brandKey)) ??
            Brand.gesband,
        _choice =
            ColorModeChoice.fromStored(_preferences.getString(colorModeKey)) {
    _rebuild();
  }

  static const brandKey = 'brand_last';
  static const colorModeKey = 'color_mode_choice';

  final SharedPreferences _preferences;
  final ProtectedImageLoader? _loadImage;
  final _logos = <String, Future<Uint8List?>>{};

  Brand _brand;
  ColorModeChoice _choice;
  late ThemeData _light;
  late ThemeData _dark;

  Brand get brand => _brand;
  ColorModeChoice get colorModeChoice => _choice;
  ThemeData get light => _light;
  ThemeData get dark => _dark;

  ThemeMode get themeMode =>
      switch (resolveDarkMode(_brand.colorMode, _choice)) {
        true => ThemeMode.dark,
        false => ThemeMode.light,
        null => ThemeMode.system,
      };

  /// Viste la app con la marca de [association] y la guarda para el
  /// próximo acceso. El logotipo llega después, sin bloquear la pantalla.
  Future<void> applyAssociation(Association association) async {
    final previous =
        _brand.associationId == association.id ? _brand.logo : null;
    _setBrand(Brand.fromAssociation(association, logo: previous));
    final logo = await logoFor(association);
    if (_brand.associationId != association.id) return;
    if (logo != null || association.logoUrl == null) {
      _setBrand(_brand.withLogo(logo));
    }
  }

  /// Logotipo de una banda, descargado una vez por sesión de la app.
  Future<Uint8List?> logoFor(Association association) {
    final url = association.logoUrl;
    final loader = _loadImage;
    if (url == null || loader == null) return Future.value(null);
    return _logos.putIfAbsent(association.id, () async {
      try {
        return await loader(url);
      } catch (_) {
        return null;
      }
    });
  }

  Future<void> setColorModeChoice(ColorModeChoice value) async {
    if (value == _choice) return;
    _choice = value;
    await _preferences.setString(colorModeKey, value.name);
    notifyListeners();
  }

  /// Al cerrar sesión se olvidan los logotipos descargados, pero se conserva
  /// la marca guardada para el siguiente acceso (decisión 0005).
  void clearSessionCache() => _logos.clear();

  void _setBrand(Brand value) {
    _brand = value;
    _rebuild();
    unawaited(_preferences.setString(brandKey, value.toStoredJson()));
    notifyListeners();
  }

  void _rebuild() {
    _light = buildGesbandTheme(_brand, Brightness.light);
    _dark = buildGesbandTheme(_brand, Brightness.dark);
  }
}

/// Da acceso a la marca y al modo de color a las pantallas.
class ThemeScope extends InheritedNotifier<ThemeController> {
  const ThemeScope({
    super.key,
    required ThemeController controller,
    required super.child,
  }) : super(notifier: controller);

  static ThemeController? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<ThemeScope>()?.notifier;

  /// Marca activa; Gesband si no hay controlador (pruebas aisladas).
  static Brand brandOf(BuildContext context) =>
      maybeOf(context)?.brand ?? Brand.gesband;
}
