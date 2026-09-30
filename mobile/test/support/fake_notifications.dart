import 'dart:async';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/features/notifications/notification_service.dart';

// Dobles de prueba del proveedor push y del servidor de dispositivos. Todos
// los identificadores y tokens son sintéticos.

const fakeToken = 'fake-push-token-0000000000000001';
const rotatedFakeToken = 'fake-push-token-0000000000000002';
const fakeDeviceId = '20000000-0000-4000-8000-000000000001';
const fakePushTestId = '30000000-0000-4000-8000-000000000001';

class FakePushGateway implements PushGateway {
  FakePushGateway({
    this.permission = PushPermission.granted,
    this.permissionAfterRequest = PushPermission.granted,
    this.token = fakeToken,
    this.failInitialize = false,
  });

  PushPermission permission;
  PushPermission permissionAfterRequest;
  String? token;
  bool failInitialize;
  PushEnvelope? initialMessage;
  final calls = <String>[];
  final tokenController = StreamController<String>.broadcast();
  final foregroundController = StreamController<PushEnvelope>.broadcast();
  final openedController = StreamController<PushEnvelope>.broadcast();

  @override
  String get platform => 'android';
  @override
  Stream<String> get tokenChanges => tokenController.stream;
  @override
  Stream<PushEnvelope> get foregroundMessages => foregroundController.stream;
  @override
  Stream<PushEnvelope> get openedMessages => openedController.stream;

  @override
  Future<void> initialize() async {
    if (failInitialize) throw StateError('Sin configuración de Firebase');
  }

  @override
  Future<PushPermission> permissionStatus() async => permission;

  @override
  Future<PushPermission> requestPermission() async {
    calls.add('requestPermission');
    permission = permissionAfterRequest;
    return permission;
  }

  @override
  Future<String?> getToken() async => token;

  @override
  Future<PushEnvelope?> getInitialMessage() async => initialMessage;

  @override
  Future<void> openSettings() async => calls.add('openSettings');

  @override
  Future<void> deleteToken() async {
    calls.add('deleteToken');
    token = null;
  }
}

/// Simula el servidor: deduce `action_required` del último estado recibido.
class FakeDeviceRepository implements DeviceRegistrationRepository {
  final calls = <String>[];
  final reports = <DeviceReport>[];
  final confirmations = <PendingPushTest>[];
  PushPermission serverPermission = PushPermission.unknown;
  bool tokenRegistered = false;
  bool receiptConfirmed = false;
  bool updateNotFound = false;
  bool confirmFailsWithNetwork = false;

  @override
  Future<DeviceRegistration> register({
    required String installationId,
    required String platform,
    required String pushToken,
    required DeviceReport report,
  }) async {
    calls.add('register');
    reports.add(report);
    serverPermission = report.permissionState;
    tokenRegistered = true;
    return _registration();
  }

  @override
  Future<DeviceRegistration> update(
    String deviceId,
    DeviceReport report,
  ) async {
    calls.add('update');
    if (updateNotFound) {
      updateNotFound = false;
      throw const ApiException('No encontrado', statusCode: 404);
    }
    reports.add(report);
    serverPermission = report.permissionState;
    return _registration();
  }

  @override
  Future<void> revoke(String deviceId) async => calls.add('revoke:$deviceId');

  @override
  Future<NotificationCapability> capability(String deviceId) async =>
      NotificationCapability(
        deviceId: deviceId,
        permissionState: serverPermission,
        tokenRegistered: tokenRegistered,
        receiptConfirmed: receiptConfirmed,
        actionRequired: switch (serverPermission) {
          PushPermission.notDetermined =>
            NotificationAction.requestSystemPermission,
          PushPermission.denied => NotificationAction.openSystemSettings,
          _ when !receiptConfirmed => NotificationAction.runReceiveTest,
          _ => NotificationAction.none,
        },
      );

  @override
  Future<PushTest> requestPushTest(
    String deviceId,
    PushPresentation presentation,
  ) async {
    calls.add('pushTest:${presentation.name}');
    return PushTest(
      id: fakePushTestId,
      expectedPresentation: presentation,
      status: PushTestStatus.queued,
    );
  }

  @override
  Future<PushTest> getPushTest(String pushTestId) async => PushTest(
        id: pushTestId,
        expectedPresentation: PushPresentation.foreground,
        status: PushTestStatus.providerFailed,
        providerErrorCode: 'unregistered',
      );

  @override
  Future<void> confirmPushTest(PendingPushTest confirmation) async {
    calls.add('confirm:${confirmation.event.wireValue}');
    if (confirmFailsWithNetwork) {
      throw const ApiException('Error de conexión');
    }
    confirmations.add(confirmation);
    receiptConfirmed = true;
  }

  DeviceRegistration _registration() => DeviceRegistration(
        id: fakeDeviceId,
        permissionState: serverPermission,
        tokenRegistered: tokenRegistered,
        active: true,
      );
}

class MemoryDeviceStateStore implements DeviceStateStore {
  String? storedDeviceId;
  bool requested = false;

  @override
  Future<String> installationId() async =>
      '40000000-0000-4000-8000-000000000001';
  @override
  Future<String?> deviceId() async => storedDeviceId;
  @override
  Future<void> saveDeviceId(String? value) async => storedDeviceId = value;
  @override
  Future<bool> permissionRequested() async => requested;
  @override
  Future<void> markPermissionRequested() async => requested = true;
}

class MemoryPendingPushTestStore implements PendingPushTestStore {
  final items = <PendingPushTest>[];

  @override
  Future<void> add(PendingPushTest value) async {
    items
      ..removeWhere((item) => item.pushTestId == value.pushTestId)
      ..add(value);
  }

  @override
  Future<List<PendingPushTest>> all() async => [...items];
  @override
  Future<void> remove(String pushTestId) async =>
      items.removeWhere((item) => item.pushTestId == pushTestId);
  @override
  Future<void> clear() async => items.clear();
}
