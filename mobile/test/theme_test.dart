import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/theme/app_theme.dart';
import 'package:gesband_mobile/core/theme/brand.dart';
import 'package:gesband_mobile/core/theme/color_contrast.dart';
import 'package:gesband_mobile/core/theme/gesband_tokens.dart';
import 'package:gesband_mobile/core/theme/theme_controller.dart';
import 'package:gesband_mobile/core/theme/visual_style.dart';

import 'support/visual_harness.dart';

const _yellow = Color(0xFFFFFF00);
const _black = Color(0xFF000000);
const _white = Color(0xFFFFFFFF);
const _aumbBlack = Color(0xFF111111);
const _gold = Color(0xFFC9A227);

Brand _brand(Color primary,
        {Color secondary = _gold, VisualStyle style = VisualStyle.escenario}) =>
    Brand(
      associationId: 'band-1',
      name: 'Banda',
      primary: primary,
      secondary: secondary,
      style: style,
    );

/// Colores de banda que ponen a prueba la legibilidad.
const _extremes = [
  _yellow,
  _black,
  _white,
  _aumbBlack,
  _gold,
  Color(0xFF7A1F2B),
  Color(0xFF1B4965),
  Color(0xFFCAE9FF),
  Color(0xFF777777),
  Color(0xFF00FF00),
  Color(0xFFFF0000),
  Color(0xFF0000FF),
];

void main() {
  group('contraste', () {
    test('lee colores hexadecimales y rechaza los no válidos', () {
      expect(parseHexColor('#1B4965'), const Color(0xFF1B4965));
      expect(parseHexColor('1b4965'), const Color(0xFF1B4965));
      expect(parseHexColor('#fff'), _white);
      expect(parseHexColor(''), isNull);
      expect(parseHexColor('#12345'), isNull);
      expect(parseHexColor('#GGGGGG'), isNull);
      expect(parseHexColor(null), isNull);
      expect(toHexColor(const Color(0xFF1B4965)), '#1B4965');
    });

    test('calcula la relación de WCAG', () {
      expect(contrastRatio(_black, _white), closeTo(21, 0.01));
      expect(contrastRatio(_white, _white), closeTo(1, 0.001));
      expect(
          contrastRatio(const Color(0xFF777777), _white), closeTo(4.48, 0.01));
    });

    test('elige tinta oscura sobre amarillo y blanca sobre negro', () {
      expect(relativeLuminance(readableInk(_yellow)), lessThan(0.05));
      expect(readableInk(_black), _white);
      expect(readableInk(_aumbBlack), _white);
      expect(relativeLuminance(readableInk(_white)), lessThan(0.05));
    });

    test('la tinta sobre cualquier color de banda alcanza 4.5:1', () {
      for (var r = 0; r <= 255; r += 51) {
        for (var g = 0; g <= 255; g += 51) {
          for (var b = 0; b <= 255; b += 51) {
            final color = Color.fromARGB(255, r, g, b);
            expect(contrastRatio(readableInk(color), color),
                greaterThanOrEqualTo(minimumTextContrast),
                reason: toHexColor(color));
          }
        }
      }
    });

    test('el amarillo se oscurece para texto sobre claro y no sobre oscuro',
        () {
      const light = Color(0xFFF4F4F2);
      const dark = Color(0xFF0F1012);
      final onLight = legibleOn(_yellow, light);
      expect(onLight, isNot(_yellow));
      expect(contrastRatio(onLight, light),
          greaterThanOrEqualTo(minimumTextContrast));
      expect(legibleOn(_yellow, dark), _yellow);
    });

    test('el negro se aclara para texto sobre oscuro y no sobre claro', () {
      const dark = Color(0xFF0F1012);
      final onDark = legibleOn(_black, dark);
      expect(contrastRatio(onDark, dark),
          greaterThanOrEqualTo(minimumTextContrast));
      expect(legibleOn(_black, _white), _black);
    });

    test('el blanco se oscurece para texto sobre blanco', () {
      final onWhite = legibleOn(_white, _white);
      expect(contrastRatio(onWhite, _white),
          greaterThanOrEqualTo(minimumTextContrast));
    });
  });

  group('tokens', () {
    for (final style in VisualStyle.values) {
      for (final brightness in Brightness.values) {
        test('$style en $brightness: neutros y estados legibles', () {
          final t =
              GesbandTokens.resolve(_brand(_gold, style: style), brightness);
          expect(t.style, style);
          expect(t.brightness, brightness);
          for (final bg in [t.background, t.surface]) {
            expect(contrastRatio(t.ink, bg), greaterThanOrEqualTo(4.5));
            expect(contrastRatio(t.muted, bg), greaterThanOrEqualTo(4.5));
          }
          for (final (bg, ink) in [
            (t.success, t.successInk),
            (t.warning, t.warningInk),
            (t.danger, t.dangerInk),
            (t.surfaceMuted, t.ink),
          ]) {
            expect(contrastRatio(ink, bg), greaterThanOrEqualTo(4.5));
          }
        });

        test('$style en $brightness: la marca nunca pinta texto ilegible', () {
          for (final primary in _extremes) {
            for (final secondary in _extremes) {
              final t = GesbandTokens.resolve(
                  _brand(primary, secondary: secondary, style: style),
                  brightness);
              final name = '${toHexColor(primary)}/${toHexColor(secondary)}';
              expect(contrastRatio(t.onPrimary, t.primary),
                  greaterThanOrEqualTo(4.5),
                  reason: 'onPrimary $name');
              expect(contrastRatio(t.primaryText, t.background),
                  greaterThanOrEqualTo(4.5),
                  reason: 'primaryText $name');
              expect(contrastRatio(t.primaryOnInk, t.onPrimary),
                  greaterThanOrEqualTo(4.5),
                  reason: 'primaryOnInk $name');
              expect(contrastRatio(t.onPrimaryTint, t.primaryTint),
                  greaterThanOrEqualTo(4.5),
                  reason: 'onPrimaryTint $name');
              expect(contrastRatio(t.onSecondary, t.secondary),
                  greaterThanOrEqualTo(4.5),
                  reason: 'onSecondary $name');
              expect(contrastRatio(t.highlight, t.surface),
                  greaterThanOrEqualTo(3),
                  reason: 'highlight $name');
            }
          }
        });
      }
    }

    test('cada estilo usa sus familias y radios', () {
      final escenario = GesbandTokens.resolve(Brand.gesband, Brightness.dark);
      expect(escenario.displayFamily, GesbandFonts.bigShouldersDisplay);
      expect(escenario.bodyFamily, GesbandFonts.instrumentSans);
      expect(escenario.displayUppercase, isTrue);
      expect(escenario.background, const Color(0xFF0F1012));
      expect(escenario.surface, const Color(0xFF1B1D21));

      final partitura = GesbandTokens.resolve(
          _brand(_gold, style: VisualStyle.partitura), Brightness.light);
      expect(partitura.displayFamily, GesbandFonts.libreCaslonText);
      expect(partitura.bodyFamily, GesbandFonts.publicSans);
      expect(partitura.background, const Color(0xFFFBFAF7));
      expect(partitura.radiusCard, lessThan(escenario.radiusCard));

      final festa = GesbandTokens.resolve(
          _brand(_gold, style: VisualStyle.festa), Brightness.light);
      expect(festa.displayFamily, GesbandFonts.bricolageGrotesque);
      expect(festa.bodyFamily, GesbandFonts.figtree);
      expect(festa.radiusButton, 999);
      expect(festa.displayCase('Hola'), 'Hola');
      expect(escenario.displayCase('Hola'), 'HOLA');
    });

    test('el ThemeData lleva los tokens y usa la versión legible del color',
        () {
      final brand = _brand(_yellow);
      final theme = buildGesbandTheme(brand, Brightness.light);
      final t = theme.extension<GesbandTokens>()!;
      expect(theme.colorScheme.primary, t.primaryText);
      expect(theme.colorScheme.primary, isNot(_yellow));
      expect(theme.scaffoldBackgroundColor, t.background);
      expect(theme.textTheme.titleLarge!.fontFamily, t.displayFamily);
      expect(theme.textTheme.bodyMedium!.fontFamily, t.bodyFamily);
      expect(
        theme.filledButtonTheme.style!.backgroundColor!.resolve({}),
        _yellow,
        reason: 'el color tal cual solo pinta fondos',
      );
      expect(theme.filledButtonTheme.style!.minimumSize!.resolve({})!.height,
          greaterThanOrEqualTo(48));
    });
  });

  group('banda con principal casi igual al fondo (AUMB: #111111 / #C9A227)',
      () {
    test('en oscuro las superficies de marca llevan borde del secundario', () {
      final t = GesbandTokens.resolve(_brand(_aumbBlack), Brightness.dark);
      expect(contrastRatio(_aumbBlack, t.background), lessThan(1.5));
      expect(t.primaryEdge, _gold);
      expect(t.primaryEdgeSide.width, inInclusiveRange(1.5, 2));
      final theme = buildGesbandTheme(_brand(_aumbBlack), Brightness.dark);
      expect(theme.filledButtonTheme.style!.side!.resolve({})!.color, _gold);
    });

    test('en claro el negro ya contrasta y no lleva borde', () {
      final t = GesbandTokens.resolve(_brand(_aumbBlack), Brightness.light);
      expect(t.primaryEdge, isNull);
      expect(t.primaryEdgeSide, BorderSide.none);
    });

    test('si el secundario tampoco contrasta se usa la línea del tema', () {
      final t = GesbandTokens.resolve(
          _brand(_aumbBlack, secondary: const Color(0xFF1A1A1A)),
          Brightness.dark);
      expect(t.primaryEdge, t.line);
    });

    test('regla aislada', () {
      expect(
        primaryEdgeFor(
          primary: _aumbBlack,
          secondary: _gold,
          background: const Color(0xFF0F1012),
          surface: const Color(0xFF1B1D21),
          line: const Color(0xFF2C2F35),
        ),
        _gold,
      );
      expect(
        primaryEdgeFor(
          primary: const Color(0xFF7A1F2B),
          secondary: _gold,
          background: const Color(0xFFF4F4F2),
          surface: _white,
          line: const Color(0xFFDADBD8),
        ),
        isNull,
      );
      // Un blanco en claro también se funde con el fondo.
      expect(
        primaryEdgeFor(
          primary: _white,
          secondary: _white,
          background: const Color(0xFFF4F4F2),
          surface: _white,
          line: const Color(0xFFDADBD8),
        ),
        const Color(0xFFDADBD8),
      );
    });
  });

  group('estilo y modo desde el API', () {
    test('lee los valores del contrato', () {
      expect(VisualStyle.fromWire('escenario'), VisualStyle.escenario);
      expect(VisualStyle.fromWire('partitura'), VisualStyle.partitura);
      expect(VisualStyle.fromWire('festa'), VisualStyle.festa);
      expect(BandColorMode.fromWire('system'), BandColorMode.system);
      expect(BandColorMode.fromWire('light'), BandColorMode.light);
      expect(BandColorMode.fromWire('dark'), BandColorMode.dark);
    });

    test('un valor desconocido o ausente cae a escenario / system', () {
      for (final value in [null, '', 'neon', 'FESTA', 3, true]) {
        expect(VisualStyle.fromWire(value), VisualStyle.escenario);
        expect(BandColorMode.fromWire(value), BandColorMode.system);
      }
    });

    test('la asociación del API trae su estilo, modo y colores', () {
      final association = Association.fromJson({
        'id': '3f0c0000-0000-4000-8000-000000000001',
        'name': 'Unió Musical de Bocairent',
        'slug': 'aumb',
        'logo_url':
            'https://gesband.fertion.com/api/v1/associations/3f0c/logo/',
        'primary_color': '#1B4965',
        'secondary_color': '#CAE9FF',
        'motto': '',
        'visual_style': 'festa',
        'color_mode': 'dark',
        'timezone': 'Europe/Madrid',
        'permissions': ['activities.view'],
      });
      expect(association.visualStyle, VisualStyle.festa);
      expect(association.colorMode, BandColorMode.dark);
      expect(association.secondaryColor, '#CAE9FF');
      expect(association.motto, isNull, reason: 'el lema vacío no se muestra');
      final brand = Brand.fromAssociation(association);
      expect(brand.primary, const Color(0xFF1B4965));
      expect(brand.secondary, const Color(0xFFCAE9FF));
      expect(brand.initials, 'UM');
    });

    test('un servidor antiguo sin los campos nuevos da Escenario y sistema',
        () {
      final association = Association.fromJson(
          associationJson(visualStyle: null, colorMode: null));
      expect(association.visualStyle, VisualStyle.escenario);
      expect(association.colorMode, BandColorMode.system);
    });

    test('colores no válidos caen a los de Gesband', () {
      final brand = Brand.fromAssociation(Association.fromJson(
          associationJson(primary: 'rojo', secondary: '#12')));
      expect(brand.primary, Brand.gesband.primary);
      expect(brand.secondary, Brand.gesband.secondary);
    });

    test('la elección de la persona manda sobre la de la banda', () {
      expect(
          resolveDarkMode(BandColorMode.system, ColorModeChoice.band), isNull);
      expect(resolveDarkMode(BandColorMode.dark, ColorModeChoice.band), true);
      expect(resolveDarkMode(BandColorMode.light, ColorModeChoice.band), false);
      expect(resolveDarkMode(BandColorMode.dark, ColorModeChoice.light), false);
      expect(resolveDarkMode(BandColorMode.light, ColorModeChoice.dark), true);
      expect(ColorModeChoice.fromStored('dark'), ColorModeChoice.dark);
      expect(ColorModeChoice.fromStored('raro'), ColorModeChoice.band);
      expect(ColorModeChoice.fromStored(null), ColorModeChoice.band);
    });

    test('monograma con iniciales significativas', () {
      expect(monogramOf('Unió Musical de Bocairent'), 'UM');
      expect(monogramOf('Banda de la Vila'), 'BV');
      expect(monogramOf('Gesband'), 'G');
      expect(monogramOf('  '), '?');
    });
  });

  group('ThemeController', () {
    late SharedPreferences preferences;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      preferences = await SharedPreferences.getInstance();
    });

    test('sin marca guardada usa Gesband con Escenario y el modo del sistema',
        () {
      final controller = ThemeController(preferences);
      expect(controller.brand.isGesband, isTrue);
      expect(controller.brand.style, VisualStyle.escenario);
      expect(controller.themeMode, ThemeMode.system);
      expect(controller.light.extension<GesbandTokens>()!.style,
          VisualStyle.escenario);
    });

    test('aplica la banda, la guarda y la recupera en el siguiente acceso',
        () async {
      final requested = <String>[];
      final controller = ThemeController(preferences, loadImage: (url) async {
        requested.add(url);
        return syntheticLogo;
      });
      final association = Association.fromJson(associationJson(
        visualStyle: 'partitura',
        colorMode: 'dark',
        logoUrl: 'https://gesband.example.test/api/v1/associations/1/logo/',
      ));
      await controller.applyAssociation(association);

      expect(controller.brand.name, 'Unió Musical de Prova');
      expect(controller.brand.logo, syntheticLogo);
      expect(controller.themeMode, ThemeMode.dark);
      expect(controller.dark.extension<GesbandTokens>()!.style,
          VisualStyle.partitura);
      expect(requested, hasLength(1));

      final next = ThemeController(preferences);
      expect(next.brand.associationId, association.id);
      expect(next.brand.style, VisualStyle.partitura);
      expect(next.brand.motto, 'Música per a tot el poble');
      expect(next.brand.logo, syntheticLogo);
      expect(next.themeMode, ThemeMode.dark);
    });

    test('no guarda logotipos de más de 120 KB', () async {
      final big = Uint8List(Brand.maxStoredLogoBytes + 1);
      final controller =
          ThemeController(preferences, loadImage: (_) async => big);
      await controller.applyAssociation(Association.fromJson(associationJson(
          logoUrl:
              'https://gesband.example.test/api/v1/associations/1/logo/')));
      expect(controller.brand.logo, big, reason: 'en memoria sí se muestra');
      expect(ThemeController(preferences).brand.logo, isNull);
    });

    test('un fallo al descargar el logotipo deja el monograma', () async {
      final controller = ThemeController(preferences,
          loadImage: (_) async => throw Exception('sin red'));
      await controller.applyAssociation(Association.fromJson(associationJson(
          logoUrl:
              'https://gesband.example.test/api/v1/associations/1/logo/')));
      expect(controller.brand.logo, isNull);
    });

    test('la elección de modo se guarda en el dispositivo', () async {
      final controller = ThemeController(preferences);
      await controller.applyAssociation(
          Association.fromJson(associationJson(colorMode: 'dark')));
      expect(controller.themeMode, ThemeMode.dark);
      await controller.setColorModeChoice(ColorModeChoice.light);
      expect(controller.themeMode, ThemeMode.light);
      expect(
          ThemeController(preferences).colorModeChoice, ColorModeChoice.light);
      await controller.setColorModeChoice(ColorModeChoice.band);
      expect(controller.themeMode, ThemeMode.dark);
    });

    test('una marca guardada dañada no rompe el arranque', () async {
      await preferences.setString(ThemeController.brandKey, '{no es json');
      expect(ThemeController(preferences).brand.isGesband, isTrue);
      await preferences.setString(
          ThemeController.brandKey, jsonEncode({'visual_style': 'festa'}));
      final brand = ThemeController(preferences).brand;
      expect(brand.style, VisualStyle.festa);
      expect(brand.primary, Brand.gesband.primary);
    });
  });
}
