import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/core/app_controller.dart';
import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/core/storage/secure_session_store.dart';
import 'package:gesband_mobile/features/polls/poll_detail_screen.dart';
import 'package:gesband_mobile/features/notifications/notification_service.dart';
import 'package:gesband_mobile/main.dart';

import 'support/fake_notifications.dart';

const _band = Association(
    id: 'band-1', name: 'Banda Sintética', timeZone: 'Europe/Madrid');

class _SignedIn implements AuthRepository {
  @override
  Future<bool> hasSession() async => true;
  @override
  Future<void> login({required String email, required String password}) async {}
  @override
  Future<void> logout() async {}
}

class _OneBand implements AssociationsRepository {
  @override
  Future<List<Association>> listMine() async => [_band];
}

class _EmptyAgenda implements ActivitiesRepository {
  @override
  Future<List<ActivitySummary>> listMine(String associationId) async => [];
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

class _OnePoll implements PollsRepository {
  final requested = <String>[];

  @override
  Future<Poll> getById(String associationId, String pollId) async {
    requested.add(pollId);
    return Poll.fromJson({
      'id': pollId,
      'question': '¿Viaje en mayo o en junio?',
      'description': '',
      'status': 'open',
      'closes_at':
          DateTime.now().toUtc().add(const Duration(days: 2)).toIso8601String(),
      'cancel_reason': '',
      'choices': [
        {'id': 'opt-a', 'label': 'Mayo'},
        {'id': 'opt-b', 'label': 'Junio'},
      ],
      'results': null,
      'participation': {'recipients': 4, 'voted': 1},
      'has_voted': false,
      'can_vote': true,
      'recipients': null,
    });
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

class _Unused implements ProfileRepository, InboxRepository, SessionStore {
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

void main() {
  late FakePushGateway gateway;
  late _OnePoll polls;
  late AppController controller;
  late LocaleController locale;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    locale = LocaleController(preferences);
    gateway = FakePushGateway();
    polls = _OnePoll();
    controller = AppController(
      api: ApiClient(
          baseUrl: 'http://localhost/api/v1', sessionStore: _Unused()),
      auth: _SignedIn(),
      associationsRepository: _OneBand(),
      activitiesRepository: _EmptyAgenda(),
      profileRepository: _Unused(),
      inboxRepository: _Unused(),
      pollsRepository: polls,
      agendaCache: AgendaCache(preferences),
      notifications: NotificationController(
        gateway: gateway,
        registrations: FakeDeviceRepository(),
        deviceStore: MemoryDeviceStateStore(),
        pendingTests: MemoryPendingPushTestStore(),
        appVersion: '0.1.0+1',
      ),
    );
  });

  Future<void> start(WidgetTester tester) async {
    // Pantalla de móvil vertical: el paso de avisos cabe entero.
    tester.view
      ..physicalSize = const Size(1080, 2340)
      ..devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      GesbandApp(controller: controller, localeController: locale),
    );
    await tester.runAsync(controller.initialize);
    await tester.pumpAndSettle();
  }

  // Las suscripciones se crearon dentro de runAsync: los eventos también
  // deben entregarse ahí para que se procesen.
  Future<void> deliver(
    WidgetTester tester,
    StreamController<PushEnvelope> stream,
    PushEnvelope envelope,
  ) async {
    await tester.runAsync(() async {
      stream.add(envelope);
      await Future<void>.delayed(const Duration(milliseconds: 10));
    });
    await tester.pumpAndSettle();
  }

  testWidgets('a poll notification opened during onboarding opens that poll',
      (tester) async {
    await start(tester);
    expect(controller.stage, AppStage.notifications);

    await deliver(
        tester,
        gateway.openedController,
        const PushEnvelope(
          messageId: 'm-1',
          data: {'kind': 'poll', 'notification_id': 'n-1', 'poll_id': 'poll-7'},
        ));
    expect(find.byType(PollDetailScreen), findsNothing);

    await tester.tap(find.byKey(const Key('continue-button')));
    await tester.pumpAndSettle();

    expect(find.byType(PollDetailScreen), findsOneWidget);
    expect(polls.requested, ['poll-7']);
  });

  testWidgets('a foreground notification shows a banner that opens the poll',
      (tester) async {
    await start(tester);
    await tester.tap(find.byKey(const Key('continue-button')));
    await tester.pumpAndSettle();
    expect(controller.stage, AppStage.ready);

    await deliver(
        tester,
        gateway.foregroundController,
        const PushEnvelope(
          messageId: 'm-2',
          title: 'Nueva encuesta',
          data: {'kind': 'poll', 'notification_id': 'n-2', 'poll_id': 'poll-8'},
        ));

    expect(find.text('Nueva encuesta'), findsOneWidget);
    await tester.tap(find.text('Abrir'));
    await tester.pumpAndSettle();

    expect(find.byType(PollDetailScreen), findsOneWidget);
    expect(polls.requested, ['poll-8']);
  });
}
