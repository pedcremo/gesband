import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/theme/brand.dart';
import 'package:gesband_mobile/core/theme/gesband_tokens.dart';
import 'package:gesband_mobile/core/theme/visual_style.dart';
import 'package:gesband_mobile/core/ui/brand_logo.dart';
import 'package:gesband_mobile/core/ui/section_nav.dart';
import 'package:gesband_mobile/features/activities/activity_detail_screen.dart';
import 'package:gesband_mobile/features/associations/association_picker_screen.dart';
import 'package:gesband_mobile/features/auth/login_screen.dart';
import 'package:gesband_mobile/features/home/home_shell.dart';
import 'package:gesband_mobile/features/notifications/notification_activation_screen.dart';
import 'package:gesband_mobile/features/polls/poll_detail_screen.dart';

import 'support/finders.dart';
import 'support/visual_harness.dart';

/// Cada pantalla principal se construye sin desbordes en los tres estilos y
/// en claro y oscuro, y muestra la marca de la banda.
void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  for (final (style, brightness) in visualMatrix) {
    final label = '${style.name} ${brightness.name}';
    final association = associationFor(style);
    final brand = Brand.fromAssociation(association);

    Future<void> check(WidgetTester tester) async {
      final t = GesbandTokens.of(tester.element(find.byType(Scaffold).first));
      expect(t.style, style);
      expect(t.brightness, brightness);
      expect(tester.takeException(), isNull);
    }

    testWidgets('acceso con la marca ($label)', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => LoginScreen(controller: controller),
          brand: brand,
          brightness: brightness);
      await check(tester);
      expect(findTextAnyCase('Unió Musical de Prova'), findsOneWidget);
      expect(find.text('Música per a tot el poble'), findsOneWidget);
      expect(find.byType(BrandLogo), findsOneWidget);
    });

    testWidgets('selector de banda ($label)', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final other = Association.fromJson(associationJson(
          id: 'band-2', name: 'Banda de la Vila', primary: '#2E5E3A'));
      final controller = await fakeAppController(prefs,
          association: association, associations: [association, other]);
      await pumpThemed(tester,
          home: () => AssociationPickerScreen(controller: controller),
          brand: brand,
          brightness: brightness);
      await check(tester);
      expect(findTextAnyCase('Banda de la Vila'), findsOneWidget);
      expect(find.byType(BrandLogo), findsNWidgets(2));
    });

    testWidgets('agenda con cartel y meses ($label)', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: brand,
          brightness: brightness);
      await check(tester);
      expect(findTextAnyCase('Unió Musical de Prova'), findsOneWidget);
      expect(find.byKey(const Key('next-activity')), findsOneWidget);
      expect(findTextAnyCase('Concierto de Santa Cecilia'), findsOneWidget);
      expect(find.byType(SectionNav), findsOneWidget);
    });

    testWidgets('secciones de la navegación ($label)', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: brand,
          brightness: brightness);

      await tester.tap(find.byKey(const Key('nav-polls')));
      await tester.pumpAndSettle();
      expect(find.text('¿Dónde hacemos el viaje de la banda?'), findsWidgets);

      await tester.tap(find.byKey(const Key('nav-inbox')));
      await tester.pumpAndSettle();
      expect(find.text('Cambio de horario'), findsOneWidget);

      await tester.tap(find.byKey(const Key('nav-profile')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('profile-card')), findsOneWidget);
      expect(find.text('Clarinete'), findsOneWidget);
      await check(tester);
    });

    testWidgets('detalle de actividad con repertorio ($label)', (tester) async {
      await pumpThemed(tester,
          home: () => ActivityDetailScreen(
                association: association,
                activityId: 'a-1',
                repository: FakeActivities(),
              ),
          brand: brand,
          brightness: brightness,
          size: const Size(390, 1400));
      await check(tester);
      expect(find.text('El Fallero'), findsOneWidget);
      expect(find.text('Autobús 1'), findsOneWidget);
      expect(find.byKey(const Key('response-buttons')), findsOneWidget);
    });

    testWidgets('detalle de encuesta ($label)', (tester) async {
      await pumpThemed(tester,
          home: () => PollDetailScreen(
                association: association,
                pollId: 'poll-1',
                repository: FakePolls(),
              ),
          brand: brand,
          brightness: brightness);
      await check(tester);
      expect(find.text('València'), findsOneWidget);
    });

    testWidgets('activación de avisos ($label)', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => NotificationActivationScreen(
                notifications: controller.notifications,
                onContinue: () {},
              ),
          brand: brand,
          brightness: brightness);
      await check(tester);
      expect(find.byKey(const Key('permission-row')), findsOneWidget);
      expect(find.byKey(const Key('continue-button')), findsOneWidget);
    });
  }

  group('texto grande (1.5) sin desbordes', () {
    for (final style in VisualStyle.values) {
      final association = associationFor(style);
      final brand = Brand.fromAssociation(association);

      testWidgets('${style.name}: acceso, agenda, secciones y detalle',
          (tester) async {
        final prefs = await SharedPreferences.getInstance();
        final controller =
            await fakeAppController(prefs, association: association);
        await pumpThemed(tester,
            home: () => LoginScreen(controller: controller),
            brand: brand,
            brightness: Brightness.light,
            textScale: 1.5,
            size: const Size(360, 740));
        expect(tester.takeException(), isNull);

        await pumpThemed(tester,
            home: () => HomeShell(controller: controller),
            brand: brand,
            brightness: Brightness.dark,
            textScale: 1.5,
            size: const Size(360, 740));
        for (final key in ['nav-polls', 'nav-inbox', 'nav-profile']) {
          await tester.tap(find.byKey(Key(key)));
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull, reason: key);
        }

        await pumpThemed(tester,
            home: () => ActivityDetailScreen(
                  association: association,
                  activityId: 'a-3',
                  repository: FakeActivities(),
                ),
            brand: brand,
            brightness: Brightness.light,
            textScale: 1.5,
            size: const Size(360, 740));
        expect(tester.takeException(), isNull);

        await pumpThemed(tester,
            home: () => NotificationActivationScreen(
                  notifications: controller.notifications,
                  onContinue: () {},
                ),
            brand: brand,
            brightness: Brightness.light,
            textScale: 1.5,
            size: const Size(360, 740));
        expect(tester.takeException(), isNull);
      });
    }
  });

  testWidgets('los tres idiomas caben en la navegación y Mi ficha',
      (tester) async {
    final association = associationFor(VisualStyle.escenario);
    for (final language in ['es', 'ca', 'en']) {
      final prefs = await SharedPreferences.getInstance();
      final controller =
          await fakeAppController(prefs, association: association);
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.dark,
          language: language,
          textScale: 1.3);
      await tester.tap(find.byKey(const Key('nav-profile')));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: language);
    }
  });
}
