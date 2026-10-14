import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/app_controller.dart';
import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/theme/brand.dart';
import 'package:gesband_mobile/core/theme/gesband_tokens.dart';
import 'package:gesband_mobile/core/theme/theme_controller.dart';
import 'package:gesband_mobile/core/theme/visual_style.dart';
import 'package:gesband_mobile/features/activities/activity_detail_screen.dart';
import 'package:gesband_mobile/features/home/home_shell.dart';
import 'package:gesband_mobile/features/polls/poll_detail_screen.dart';
import 'package:gesband_mobile/main.dart';

import 'support/finders.dart';
import 'support/visual_harness.dart';

const _gold = Color(0xFFC9A227);

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  group('banda negra en oscuro (AUMB: #111111 / #C9A227)', () {
    final association = associationFor(VisualStyle.escenario,
        primary: '#111111', secondary: '#C9A227');

    testWidgets('cartel, píldora activa y logotipo llevan borde dorado',
        (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.dark);

      BorderSide sideOf(Finder finder) {
        final material = tester.widget<Material>(finder);
        return (material.shape! as RoundedRectangleBorder).side;
      }

      final poster = sideOf(find.byKey(const Key('next-activity')));
      expect(poster.color, _gold);
      expect(poster.width, inInclusiveRange(1.5, 2));

      final activeNav = sideOf(find.byKey(const Key('nav-agenda')));
      expect(activeNav.color, _gold);
      expect(sideOf(find.byKey(const Key('nav-polls'))), BorderSide.none,
          reason: 'solo la pestaña rellena lleva borde');

      final logo =
          tester.widget<Container>(find.byKey(const Key('brand-logo')).first);
      final border =
          (logo.foregroundDecoration! as BoxDecoration).border! as Border;
      expect(border.top.color, _gold);
    });

    testWidgets('en claro el negro contrasta y no lleva borde', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.light);

      final material =
          tester.widget<Material>(find.byKey(const Key('next-activity')));
      expect((material.shape! as RoundedRectangleBorder).side, BorderSide.none);
    });
  });

  group('cartel de la próxima convocatoria', () {
    final association = associationFor(VisualStyle.escenario);

    Future<(AppController, FakeActivities)> open(WidgetTester tester,
        {List<Map<String, dynamic>>? agenda, DateTime? cachedAt}) async {
      final prefs = await SharedPreferences.getInstance();
      final activities = FakeActivities(agenda: agenda, cachedAt: cachedAt);
      final controller = await fakeAppController(prefs,
          association: association, activities: activities);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.dark);
      return (controller, activities);
    }

    testWidgets('«Asistiré» responde desde la agenda', (tester) async {
      final (_, activities) = await open(tester);

      await tester.tap(find.byKey(const Key('poster-accept')));
      await tester.pumpAndSettle();

      expect(activities.sent.single, ('a-1', InvitationResponse.accepted, ''));
      expect(find.text('Respuesta guardada.'), findsOneWidget);
      final accept =
          tester.widget<FilledButton>(find.byKey(const Key('poster-accept')));
      expect(accept.onPressed, isNull,
          reason: 'la respuesta elegida queda marcada');
    });

    testWidgets('«No podré» en una obligatoria pide el motivo', (tester) async {
      final (_, activities) = await open(tester, agenda: [
        activityJson(
          id: 'm-1',
          title: 'Procesión',
          startsIn: const Duration(days: 3),
          mandatory: true,
        ),
      ]);

      await tester.tap(find.byKey(const Key('poster-decline')));
      await tester.pumpAndSettle();
      expect(find.text('Comunicar ausencia'), findsOneWidget);
      expect(activities.sent, isEmpty);

      await tester.enterText(find.byType(TextField), 'Viaje de trabajo');
      await tester.tap(find.text('Comunicar ausencia'));
      await tester.pumpAndSettle();

      expect(activities.sent.single,
          ('m-1', InvitationResponse.declined, 'Viaje de trabajo'));
    });

    testWidgets('cancelar el motivo no envía nada', (tester) async {
      final (_, activities) = await open(tester, agenda: [
        activityJson(
          id: 'm-1',
          title: 'Procesión',
          startsIn: const Duration(days: 3),
          mandatory: true,
        ),
      ]);

      await tester.tap(find.byKey(const Key('poster-decline')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancelar'));
      await tester.pumpAndSettle();

      expect(activities.sent, isEmpty);
    });

    testWidgets('sin conexión el cartel no ofrece responder', (tester) async {
      await open(tester, cachedAt: DateTime(2026, 10, 1, 12, 34));

      expect(find.byKey(const Key('offline-agenda')), findsOneWidget);
      expect(find.byKey(const Key('next-activity')), findsOneWidget);
      expect(find.byKey(const Key('poster-accept')), findsNothing);
    });

    testWidgets('pulsar el cartel abre el detalle', (tester) async {
      await open(tester);

      await tester.tap(findTextAnyCase('Concierto de Santa Cecilia'));
      await tester.pumpAndSettle();

      expect(find.byType(ActivityDetailScreen), findsOneWidget);
    });

    testWidgets('agenda vacía', (tester) async {
      await open(tester, agenda: []);

      expect(find.text('No tienes próximas actividades.'), findsOneWidget);
      expect(find.byKey(const Key('next-activity')), findsNothing);
    });
  });

  group('Mi ficha', () {
    final association = Association.fromJson(
        associationJson(visualStyle: 'festa', colorMode: 'dark'));

    testWidgets('«Claro» se aplica y se guarda; «Como la banda» vuelve',
        (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      final (:theme, :locale) = await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.dark);
      await tester.tap(find.byKey(const Key('nav-profile')));
      await tester.pumpAndSettle();

      // Los ajustes quedan bajo la foto y «Lo que se me debe».
      await tester.ensureVisible(find.byKey(const Key('color-mode-choice')));
      await tester.pumpAndSettle();
      await tester
          .tap(find.byKey(const ValueKey('choice-ColorModeChoice.light')));
      await tester.pumpAndSettle();
      expect(theme.themeMode, ThemeMode.light);
      expect(prefs.getString(ThemeController.colorModeKey), 'light');
      expect(
          GesbandTokens.of(tester.element(find.byType(HomeShell))).brightness,
          Brightness.light);

      await tester
          .tap(find.byKey(const ValueKey('choice-ColorModeChoice.band')));
      await tester.pumpAndSettle();
      expect(theme.themeMode, ThemeMode.dark,
          reason: 'la banda tiene color_mode dark');
    });

    testWidgets('el idioma se cambia desde Mi ficha', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      final (:theme, :locale) = await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.light);
      await tester.tap(find.byKey(const Key('nav-profile')));
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.byKey(const Key('language-choice')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('choice-ca')));
      await tester.pumpAndSettle();

      expect(locale.locale.languageCode, 'ca');
      expect(findTextAnyCase('La meua fitxa'), findsWidgets);
    });

    testWidgets('sin ficha vinculada los ajustes siguen disponibles',
        (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller = await fakeAppController(prefs,
          association: association, profile: FakeProfile(fail: true));
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.light);
      await tester.tap(find.byKey(const Key('nav-profile')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('profile-unavailable')), findsOneWidget);
      expect(find.byKey(const Key('color-mode-choice')), findsOneWidget);
      await tester.ensureVisible(find.byKey(const Key('sign-out')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('sign-out')), findsOneWidget);
    });

    testWidgets('los avisos se revisan desde ajustes (MUST-NOTIF-01)',
        (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.light);
      await tester.tap(find.byKey(const Key('nav-profile')));
      await tester.pumpAndSettle();

      // Hasta el final, para que la fila no quede bajo la navegación.
      await tester.ensureVisible(find.byKey(const Key('sign-out')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('notifications-settings')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('permission-row')), findsOneWidget);
    });
  });

  testWidgets('un aviso se marca leído y abre su encuesta', (tester) async {
    final association = associationFor(VisualStyle.partitura);
    final prefs = await SharedPreferences.getInstance();
    final inbox = FakeInbox();
    final controller =
        await fakeAppController(prefs, association: association, inbox: inbox);
    // `openTarget` navega cuando la app está lista.
    controller.finishNotificationStep();
    await pumpThemed(tester,
        home: () => Navigator(
              key: controller.navigatorKey,
              onGenerateRoute: (_) => MaterialPageRoute<void>(
                builder: (_) => HomeShell(controller: controller),
              ),
            ),
        brand: Brand.fromAssociation(association),
        brightness: Brightness.light);
    await tester.tap(find.byKey(const Key('nav-inbox')));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Nueva encuesta'));
    await tester.pumpAndSettle();
    expect(inbox.marked, isEmpty, reason: 'ya estaba leído');
    expect(find.byType(PollDetailScreen), findsOneWidget);

    Navigator.of(tester.element(find.byType(PollDetailScreen))).pop();
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cambio de horario'));
    await tester.pumpAndSettle();
    expect(inbox.marked, ['n-1']);
    expect(find.byType(ActivityDetailScreen), findsOneWidget);
  });

  testWidgets('la marca sigue a la banda elegida y se recuerda en el acceso',
      (tester) async {
    tester.view
      ..physicalSize = const Size(1170, 2532)
      ..devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    final prefs = await SharedPreferences.getInstance();
    final first = Association.fromJson(associationJson(
        id: 'band-1', name: 'Banda Primera', visualStyle: 'partitura'));
    final second = Association.fromJson(associationJson(
        id: 'band-2',
        name: 'Banda Segunda',
        visualStyle: 'festa',
        primary: '#2E5E3A'));
    final controller = await fakeAppController(prefs,
        association: first, associations: [first, second]);
    final theme = ThemeController(prefs);
    final locale = LocaleController(prefs);
    await tester.pumpWidget(GesbandApp(
      controller: controller,
      localeController: locale,
      themeController: theme,
    ));
    await tester.pumpAndSettle();
    expect(theme.brand.isGesband, isTrue,
        reason: 'sin banda elegida ni guardada, Gesband');

    controller.selectAssociation(first);
    await tester.pumpAndSettle();
    expect(theme.brand.name, 'Banda Primera');
    expect(theme.brand.style, VisualStyle.partitura);

    controller.changeAssociation();
    await tester.pumpAndSettle();
    expect(theme.brand.name, 'Banda Primera',
        reason: 'mientras se elige se conserva la última');
    controller.selectAssociation(second);
    await tester.pumpAndSettle();
    expect(theme.brand.name, 'Banda Segunda');
    expect(theme.light.extension<GesbandTokens>()!.style, VisualStyle.festa);

    await tester.runAsync(controller.logout);
    await tester.pumpAndSettle();
    expect(controller.stage, AppStage.signedOut);
    expect(findTextAnyCase('Banda Segunda'), findsOneWidget,
        reason: 'el acceso muestra la última banda');
    expect(ThemeController(prefs).brand.name, 'Banda Segunda');
  });
}
