import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/theme/brand.dart';
import 'package:gesband_mobile/core/theme/visual_style.dart';
import 'package:gesband_mobile/features/activities/activity_detail_screen.dart';
import 'package:gesband_mobile/features/home/home_shell.dart';

import 'support/earnings_fixtures.dart';
import 'support/visual_harness.dart';

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  final association = associationFor(VisualStyle.escenario);

  Future<void> pumpDetail(
    WidgetTester tester,
    Map<String, dynamic> pay, {
    String language = 'es',
  }) async {
    final activities = FakeActivities(agenda: [
      activityJson(
          id: 'a-1',
          title: 'Concierto de Santa Cecilia',
          startsIn: const Duration(days: 2),
          pay: pay),
    ]);
    await pumpThemed(
      tester,
      home: () => ActivityDetailScreen(
        association: association,
        activityId: 'a-1',
        repository: activities,
      ),
      brand: Brand.fromAssociation(association),
      brightness: Brightness.light,
      language: language,
    );
  }

  String? paidText(WidgetTester tester, Key key) {
    final texts =
        find.descendant(of: find.byKey(key), matching: find.byType(Text));
    return texts.evaluate().isEmpty
        ? null
        : (texts.evaluate().first.widget as Text).data;
  }

  group('detalle de actividad', () {
    testWidgets('una remunerada indica su importe', (tester) async {
      await pumpDetail(tester, paidActivityFields);

      expect(paidText(tester, const Key('paid-indicator')),
          'Remunerada · 25,00 €');
    });

    testWidgets('el importe sigue el idioma', (tester) async {
      await pumpDetail(tester, paidActivityFields, language: 'en');

      expect(paidText(tester, const Key('paid-indicator')), 'Paid · €25.00');
    });

    testWidgets('sin importe fijado solo dice que es remunerada',
        (tester) async {
      await pumpDetail(tester, {'is_paid': true, 'fee_amount': null});

      expect(paidText(tester, const Key('paid-indicator')), 'Remunerada');
    });

    testWidgets('una no remunerada no muestra nada', (tester) async {
      await pumpDetail(tester, unpaidActivityFields);

      expect(find.byKey(const Key('paid-indicator')), findsNothing);
      expect(find.textContaining('Remunerada'), findsNothing);
      expect(find.textContaining('€'), findsNothing);
    });
  });

  group('cartel de la agenda', () {
    for (final style in VisualStyle.values) {
      testWidgets('una remunerada lo indica (${style.name})', (tester) async {
        final band = associationFor(style);
        final prefs = await SharedPreferences.getInstance();
        final controller = await fakeAppController(prefs, association: band);
        await pumpThemed(tester,
            home: () => HomeShell(controller: controller),
            brand: Brand.fromAssociation(band),
            brightness: Brightness.dark);

        final paid = find.descendant(
            of: find.byKey(const Key('next-activity')),
            matching: find.byKey(const Key('poster-paid')));
        expect(paid, findsOneWidget);
        expect(
            paidText(tester, const Key('poster-paid')), 'Remunerada · 25,00 €');
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('una no remunerada no lo indica', (tester) async {
      final prefs = await SharedPreferences.getInstance();
      final controller = await fakeAppController(prefs,
          association: association,
          activities: FakeActivities(agenda: [
            activityJson(
                id: 'a-2',
                title: 'Ensayo general',
                startsIn: const Duration(days: 5)),
          ]));
      await pumpThemed(tester,
          home: () => HomeShell(controller: controller),
          brand: Brand.fromAssociation(association),
          brightness: Brightness.light);

      expect(find.byKey(const Key('next-activity')), findsOneWidget);
      expect(find.byKey(const Key('poster-paid')), findsNothing);
    });
  });
}
