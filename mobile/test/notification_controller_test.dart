import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:gesband_mobile/features/notifications/notification_activation_screen.dart';
import 'package:gesband_mobile/features/notifications/notification_service.dart';

import 'support/fake_notifications.dart';

PushEnvelope _testMessage() => const PushEnvelope(
      messageId: 'm-1',
      data: {'kind': 'notification_test', 'push_test_id': fakePushTestId},
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FakePushGateway gateway;
  late FakeDeviceRepository repository;
  late MemoryDeviceStateStore store;
  late MemoryPendingPushTestStore pending;
  late NotificationController controller;

  NotificationController build() => NotificationController(
        gateway: gateway,
        registrations: repository,
        deviceStore: store,
        pendingTests: pending,
        appVersion: '0.1.0+1',
        languageCode: 'ca',
        clock: () => DateTime.utc(2026, 9, 30, 18, 5, 9, 123),
      );

  setUp(() {
    gateway = FakePushGateway();
    repository = FakeDeviceRepository();
    store = MemoryDeviceStateStore();
    pending = MemoryPendingPushTestStore();
    controller = build();
  });

  tearDown(() => controller.dispose());

  test('registers the device with the observed granted permission', () async {
    await controller.initialize();
    await controller.bindSession();

    expect(repository.calls.first, 'register');
    final report = repository.reports.single;
    expect(report.permissionState, PushPermission.granted);
    expect(report.pushToken, fakeToken);
    expect(report.locale, 'ca-ES-valencia');
    expect(store.storedDeviceId, fakeDeviceId);
    expect(controller.state.tokenRegistered, isTrue);
    expect(controller.state.receiptConfirmed, isFalse);
    expect(controller.state.nextAction, NotificationAction.runReceiveTest);
  });

  test('asks once and then points to settings when permission is denied',
      () async {
    // Android informa «denegado» antes de preguntar por primera vez.
    gateway
      ..permission = PushPermission.denied
      ..permissionAfterRequest = PushPermission.denied;
    await controller.initialize();
    await controller.bindSession();

    expect(
        repository.reports.last.permissionState, PushPermission.notDetermined);
    expect(controller.state.nextAction,
        NotificationAction.requestSystemPermission);

    await controller.requestPermission();

    // El token se registra igualmente: el servidor decide qué hacer.
    expect(repository.reports.last.permissionState, PushPermission.denied);
    expect(repository.tokenRegistered, isTrue);
    expect(controller.state.nextAction, NotificationAction.openSystemSettings);
    expect(gateway.calls.where((call) => call == 'requestPermission'),
        hasLength(1));
  });

  test('detects revocation from settings on resume and reports it', () async {
    await controller.initialize();
    await controller.bindSession();
    final deactivations = <void>[];
    controller.deactivations.listen(deactivations.add);

    gateway.permission = PushPermission.denied;
    store.requested = true;
    controller.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await pumpEventQueue();

    expect(repository.calls.last, 'update');
    expect(repository.reports.last.permissionState, PushPermission.denied);
    // El token no ha cambiado, así que no se reenvía.
    expect(repository.reports.last.pushToken, isNull);
    expect(deactivations, hasLength(1));
    expect(controller.state.nextAction, NotificationAction.openSystemSettings);

    gateway.permission = PushPermission.granted;
    controller.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await pumpEventQueue();

    expect(repository.reports.last.permissionState, PushPermission.granted);
    expect(controller.state.nextAction, NotificationAction.runReceiveTest);
  });

  test('sends a rotated token with PATCH', () async {
    await controller.initialize();
    await controller.bindSession();

    gateway.token = rotatedFakeToken;
    gateway.tokenController.add(rotatedFakeToken);
    await pumpEventQueue();

    expect(repository.calls.where((call) => call == 'register'), hasLength(1));
    expect(
      repository.reports.map((report) => report.pushToken),
      [fakeToken, rotatedFakeToken, null],
    );
    expect(repository.calls.skip(1), everyElement('update'));
  });

  test('registers again when the server no longer knows the device', () async {
    store.storedDeviceId = '20000000-0000-4000-8000-000000000099';
    repository.updateNotFound = true;
    await controller.initialize();
    await controller.bindSession();

    expect(repository.calls, containsAllInOrder(['update', 'register']));
    expect(store.storedDeviceId, fakeDeviceId);
  });

  test('confirms a foreground test with received_foreground in UTC', () async {
    await controller.initialize();
    await controller.bindSession();
    await controller.sendTest(PushPresentation.foreground);
    expect(repository.calls, contains('pushTest:foreground'));

    gateway.foregroundController.add(_testMessage());
    await pumpEventQueue();

    final confirmation = repository.confirmations.single;
    expect(confirmation.pushTestId, fakePushTestId);
    expect(confirmation.event, PushTestEvent.receivedForeground);
    expect(formatUtc(confirmation.occurredAt), '2026-09-30T18:05:09Z');
    expect(controller.state.receiptConfirmed, isTrue);
    expect(
        controller.state.lastTest?.status, PushTestStatus.receivedForeground);
    expect(pending.items, isEmpty);
  });

  test('keeps a background test until a session can confirm it', () async {
    // Recibida con la app cerrada y sin sesión: el manejador la guardó.
    await pending.add(PendingPushTest.openedFromBackground(
      fakePushTestId,
      occurredAt: DateTime.utc(2026, 9, 30, 17),
    ));
    gateway.initialMessage = _testMessage();
    await controller.initialize();
    expect(repository.confirmations, isEmpty);

    await controller.bindSession();

    expect(repository.confirmations.single.event,
        PushTestEvent.openedFromBackground);
    expect(pending.items, isEmpty);
  });

  test('retries a confirmation that failed for lack of network', () async {
    await controller.initialize();
    await controller.bindSession();
    repository.confirmFailsWithNetwork = true;

    gateway.openedController.add(_testMessage());
    await pumpEventQueue();
    expect(pending.items, hasLength(1));
    expect(controller.state.error, AppMessage.notificationConfirmationFailed);

    repository.confirmFailsWithNetwork = false;
    controller.didChangeAppLifecycleState(AppLifecycleState.resumed);
    await pumpEventQueue();

    expect(repository.confirmations.single.event,
        PushTestEvent.openedFromBackground);
    expect(pending.items, isEmpty);
  });

  test('sign out revokes the device before deleting the token', () async {
    await controller.initialize();
    await controller.bindSession();
    await pending.add(PendingPushTest.openedFromBackground(
      '30000000-0000-4000-8000-000000000002',
      occurredAt: DateTime.utc(2026, 9, 30),
    ));

    await controller.unbindSession();

    expect(repository.calls.last, 'revoke:$fakeDeviceId');
    expect(gateway.calls.last, 'deleteToken');
    expect(store.storedDeviceId, isNull);
    expect(pending.items, isEmpty);
    expect(controller.state.tokenRegistered, isFalse);

    // Un aviso que llegue después no se muestra ni se abre en otra sesión.
    final foreground = <PushEnvelope>[];
    controller.foregroundMessages.listen(foreground.add);
    gateway.foregroundController.add(const PushEnvelope(
      messageId: 'm-2',
      data: {'kind': 'activity', 'activity_id': 'a-1'},
    ));
    await pumpEventQueue();
    expect(foreground, isEmpty);
  });

  test('opens the poll or the activity named by the notification', () async {
    await controller.initialize();
    await controller.bindSession();
    final targets = <NotificationTarget>[];
    controller.targets.listen(targets.add);

    gateway.openedController
      ..add(const PushEnvelope(messageId: 'm-3', data: {
        'kind': 'poll',
        'notification_id': 'n-1',
        'poll_id': 'poll-1',
        'activity_id': 'activity-1',
      }))
      ..add(const PushEnvelope(messageId: 'm-4', data: {
        'kind': 'activity',
        'notification_id': 'n-2',
        'activity_id': 'activity-2',
      }));
    await pumpEventQueue();

    expect(targets, [
      const PollTarget('poll-1'),
      const ActivityTarget('activity-2'),
    ]);
  });

  test('stays usable when Firebase cannot start', () async {
    gateway.failInitialize = true;
    await controller.initialize();
    await controller.bindSession();

    expect(controller.state.available, isFalse);
    expect(controller.state.error, AppMessage.notificationsInitializeFailed);
    expect(controller.state.nextAction, NotificationAction.none);
    expect(repository.calls, isEmpty);
  });

  group('activation screen', () {
    late LocaleController locale;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      locale = LocaleController(await SharedPreferences.getInstance());
    });

    Future<void> pumpScreen(WidgetTester tester, {VoidCallback? onContinue}) =>
        tester.pumpWidget(MaterialApp(
          builder: (context, child) =>
              LocaleScope(controller: locale, child: child!),
          locale: const Locale('es'),
          localizationsDelegates: const [
            AppStrings.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppStrings.supportedLocales,
          home: NotificationActivationScreen(
            notifications: controller,
            onContinue: onContinue ?? () {},
          ),
        ));

    testWidgets('offers settings instead of a new request after a denial',
        (tester) async {
      gateway.permission = PushPermission.denied;
      store.requested = true;
      await tester.runAsync(() async {
        await controller.initialize();
        await controller.bindSession();
      });
      await pumpScreen(tester);

      expect(find.byKey(const Key('open-settings-button')), findsOneWidget);
      expect(find.byKey(const Key('request-permission-button')), findsNothing);
      expect(find.text('Permiso: denegado'), findsOneWidget);
      expect(find.text('Dispositivo registrado: sí'), findsOneWidget);
      expect(find.text('Recepción comprobada: pendiente'), findsOneWidget);

      await tester.tap(find.byKey(const Key('open-settings-button')));
      expect(gateway.calls, contains('openSettings'));
    });

    testWidgets('shows provisional as such, not as enabled', (tester) async {
      gateway.permission = PushPermission.provisional;
      await tester.runAsync(() async {
        await controller.initialize();
        await controller.bindSession();
      });
      await pumpScreen(tester);

      expect(find.text('Permiso: provisional (avisos silenciosos)'),
          findsOneWidget);
      expect(controller.state.fullyActive, isFalse);
    });

    testWidgets('lets the person continue when push is unavailable',
        (tester) async {
      gateway.failInitialize = true;
      var continued = false;
      await tester.runAsync(controller.initialize);
      await pumpScreen(tester, onContinue: () => continued = true);

      expect(find.textContaining('no están disponibles'), findsOneWidget);
      await tester.tap(find.byKey(const Key('continue-button')));
      expect(continued, isTrue);
    });
  });
}
