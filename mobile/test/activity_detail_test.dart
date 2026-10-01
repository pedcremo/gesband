import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/features/activities/activity_detail_screen.dart';

const _band =
    Association(id: 'band-1', name: 'Banda', timeZone: 'Europe/Madrid');

/// Responde como el servidor real: `my_invitation` y `my_transport`.
class _FakeActivities implements ActivitiesRepository {
  _FakeActivities({
    this.response = 'accepted',
    this.mandatory = false,
    this.deadline,
    this.reconfirm = false,
    this.fail = false,
  });

  String response;
  final bool mandatory;
  final DateTime? deadline;
  final bool reconfirm;
  final bool fail;
  final sent = <(InvitationResponse, String)>[];

  ActivityDetail _current() => ActivityDetail.fromJson({
        'id': 'activity-1',
        'title': 'Processó de Sant Blai',
        'kind': 'performance',
        'status': 'published',
        'starts_at': DateTime.now()
            .toUtc()
            .add(const Duration(days: 3))
            .toIso8601String(),
        'location': 'Plaça Major',
        'uniform': 'Gala',
        'is_mandatory': mandatory,
        'response_deadline': deadline?.toUtc().toIso8601String(),
        'programme': const [],
        'invitations': const [],
        'my_invitation': {
          'id': 'invitation-1',
          'response': response,
          'needs_reconfirmation': reconfirm,
        },
        'my_transport': {
          'label': 'Autobús 1',
          'meeting_point': 'Estación',
          'driver_name': 'Pep Conductor',
        },
      });

  @override
  Future<ActivityDetail> getById(
          String associationId, String activityId) async =>
      _current();

  @override
  Future<ActivityDetail> respond(
    String associationId,
    String activityId,
    InvitationResponse value, {
    String note = '',
  }) async {
    if (fail) throw Exception('sin red');
    sent.add((value, note));
    response = value.name;
    return _current();
  }

  @override
  Future<List<ActivitySummary>> listMine(String associationId) async => [];
}

Future<void> _open(WidgetTester tester, ActivitiesRepository repository) async {
  SharedPreferences.setMockInitialValues({});
  final preferences = await SharedPreferences.getInstance();
  await tester.pumpWidget(LocaleScope(
    controller: LocaleController(preferences),
    child: MaterialApp(
      locale: const Locale('es'),
      localizationsDelegates: const [
        AppStrings.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppStrings.supportedLocales,
      home: ActivityDetailScreen(
        association: _band,
        activityId: 'activity-1',
        repository: repository,
      ),
    ),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows the current reply, place and transport', (tester) async {
    await _open(tester, _FakeActivities());

    expect(find.text('Asistirás'), findsOneWidget);
    expect(find.text('Plaça Major'), findsOneWidget);
    expect(find.textContaining('Autobús 1'), findsOneWidget);
    expect(find.textContaining('Pep Conductor'), findsOneWidget);
  });

  testWidgets('changing the reply is sent and confirmed on screen',
      (tester) async {
    final repository = _FakeActivities();
    await _open(tester, repository);

    await tester.tap(find.text('No asistiré'));
    await tester.pumpAndSettle();

    expect(repository.sent.single.$1, InvitationResponse.declined);
    expect(find.text('No asistirás'), findsOneWidget);
    expect(find.text('Respuesta guardada.'), findsOneWidget);
  });

  testWidgets('a mandatory activity asks for the reason before declining',
      (tester) async {
    final repository = _FakeActivities(mandatory: true);
    await _open(tester, repository);

    await tester.tap(find.text('No asistiré'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Viaje de trabajo');
    await tester.tap(find.text('Comunicar ausencia'));
    await tester.pumpAndSettle();

    expect(repository.sent.single,
        (InvitationResponse.declined, 'Viaje de trabajo'));
  });

  testWidgets('a failed reply is reported and the old one stays',
      (tester) async {
    await _open(tester, _FakeActivities(fail: true));

    await tester.tap(find.text('No asistiré'));
    await tester.pumpAndSettle();

    expect(
        find.textContaining('No se pudo guardar la respuesta'), findsOneWidget);
    expect(find.text('Asistirás'), findsOneWidget);
  });

  testWidgets('after the deadline the reply cannot be changed', (tester) async {
    await _open(
      tester,
      _FakeActivities(
          deadline: DateTime.now().subtract(const Duration(hours: 1))),
    );

    expect(find.text('El plazo de respuesta ha terminado.'), findsOneWidget);
    expect(find.byKey(const Key('response-buttons')), findsNothing);
  });

  testWidgets('a change of date asks to confirm again', (tester) async {
    await _open(tester, _FakeActivities(response: 'pending', reconfirm: true));

    expect(find.textContaining('vuelve a confirmar'), findsOneWidget);
    expect(find.text('Sin responder'), findsOneWidget);
  });
}
