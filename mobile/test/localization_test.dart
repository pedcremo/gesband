import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('supports coherent Spanish, Valencian and English strings', () {
    expect(
      AppStrings.supportedLocales.map((locale) => locale.languageCode),
      ['es', 'ca', 'en'],
    );
    expect(AppStrings(const Locale('es')).activity, 'Actividad');
    expect(AppStrings(const Locale('ca')).activity, 'Activitat');
    expect(AppStrings(const Locale('en')).activity, 'Activity');
  });

  test('persists and restores the selected locale', () async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    final controller = LocaleController(preferences);

    expect(controller.locale, const Locale('es'));
    await controller.setLocale(const Locale('ca'));

    expect(controller.locale, const Locale('ca'));
    expect(
      LocaleController(preferences).locale,
      const Locale('ca'),
    );
  });

  test('ignores unsupported locales', () async {
    SharedPreferences.setMockInitialValues({'app_locale': 'en'});
    final preferences = await SharedPreferences.getInstance();
    final controller = LocaleController(preferences);

    await controller.setLocale(const Locale('fr'));

    expect(controller.locale, const Locale('en'));
    expect(preferences.getString('app_locale'), 'en');
  });
}
