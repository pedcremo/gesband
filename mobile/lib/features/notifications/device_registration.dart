import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../../core/api/api_client.dart';
import 'pending_push_tests.dart';
import 'push_gateway.dart';

/// Idioma del dispositivo tal como lo espera el servidor para los avisos.
String deviceLocaleTag(String languageCode) => switch (languageCode) {
      'ca' => 'ca-ES-valencia',
      'en' => 'en',
      _ => 'es-ES',
    };

DateTime? _parseUtc(Object? value) =>
    value is String ? DateTime.tryParse(value)?.toUtc() : null;

class DeviceRegistration {
  const DeviceRegistration({
    required this.id,
    required this.permissionState,
    required this.tokenRegistered,
    required this.active,
    this.revokedAt,
  });

  factory DeviceRegistration.fromJson(Map<String, dynamic> json) =>
      DeviceRegistration(
        id: json['id'] as String,
        permissionState:
            PushPermission.fromWire(json['permission_state'] as String?),
        tokenRegistered: json['token_registered'] as bool? ?? false,
        active: json['active'] as bool? ?? false,
        revokedAt: _parseUtc(json['revoked_at']),
      );

  final String id;
  final PushPermission permissionState;
  final bool tokenRegistered;
  final bool active;
  final DateTime? revokedAt;
}

/// Siguiente paso que el servidor propone para completar MUST-NOTIF-01.
enum NotificationAction {
  none('none'),
  requestSystemPermission('request_system_permission'),
  openSystemSettings('open_system_settings'),
  registerToken('register_token'),
  runReceiveTest('run_receive_test');

  const NotificationAction(this.wireValue);
  final String wireValue;

  static NotificationAction fromWire(String? value) =>
      NotificationAction.values.firstWhere(
        (item) => item.wireValue == value,
        orElse: () => NotificationAction.registerToken,
      );
}

class NotificationCapability {
  const NotificationCapability({
    required this.deviceId,
    required this.permissionState,
    required this.tokenRegistered,
    required this.receiptConfirmed,
    required this.actionRequired,
    this.lastReceiptConfirmedAt,
  });

  factory NotificationCapability.fromJson(Map<String, dynamic> json) =>
      NotificationCapability(
        deviceId: json['device_id'] as String,
        permissionState:
            PushPermission.fromWire(json['permission_state'] as String?),
        tokenRegistered: json['token_registered'] as bool? ?? false,
        receiptConfirmed: json['receipt_confirmed'] as bool? ?? false,
        lastReceiptConfirmedAt: _parseUtc(json['last_receipt_confirmed_at']),
        actionRequired:
            NotificationAction.fromWire(json['action_required'] as String?),
      );

  final String deviceId;
  final PushPermission permissionState;
  final bool tokenRegistered;
  final bool receiptConfirmed;
  final DateTime? lastReceiptConfirmedAt;
  final NotificationAction actionRequired;
}

enum PushPresentation { foreground, background }

enum PushTestStatus {
  queued('queued'),
  providerAccepted('provider_accepted'),
  providerFailed('provider_failed'),
  receivedForeground('received_foreground'),
  openedFromBackground('opened_from_background'),
  expired('expired');

  const PushTestStatus(this.wireValue);
  final String wireValue;

  static PushTestStatus fromWire(String? value) =>
      PushTestStatus.values.firstWhere(
        (item) => item.wireValue == value,
        orElse: () => PushTestStatus.queued,
      );

  bool get confirmed =>
      this == receivedForeground || this == openedFromBackground;
}

class PushTest {
  const PushTest({
    required this.id,
    required this.expectedPresentation,
    required this.status,
    this.providerErrorCode,
  });

  factory PushTest.fromJson(Map<String, dynamic> json) => PushTest(
        id: json['id'] as String,
        expectedPresentation: json['expected_presentation'] == 'background'
            ? PushPresentation.background
            : PushPresentation.foreground,
        status: PushTestStatus.fromWire(json['status'] as String?),
        providerErrorCode: json['provider_error_code'] as String?,
      );

  final String id;
  final PushPresentation expectedPresentation;
  final PushTestStatus status;
  final String? providerErrorCode;

  PushTest withStatus(PushTestStatus value) => PushTest(
        id: id,
        expectedPresentation: expectedPresentation,
        status: value,
        providerErrorCode: providerErrorCode,
      );
}

/// Campos que se envían al registrar o actualizar un dispositivo. En una
/// actualización, los nulos no se envían.
class DeviceReport {
  const DeviceReport({
    required this.permissionState,
    required this.appVersion,
    required this.locale,
    this.pushToken,
  });

  final PushPermission permissionState;
  final String appVersion;
  final String locale;
  final String? pushToken;
}

abstract interface class DeviceRegistrationRepository {
  Future<DeviceRegistration> register({
    required String installationId,
    required String platform,
    required String pushToken,
    required DeviceReport report,
  });
  Future<DeviceRegistration> update(String deviceId, DeviceReport report);
  Future<void> revoke(String deviceId);
  Future<NotificationCapability> capability(String deviceId);
  Future<PushTest> requestPushTest(
    String deviceId,
    PushPresentation presentation,
  );
  Future<PushTest> getPushTest(String pushTestId);
  Future<void> confirmPushTest(PendingPushTest confirmation);
}

class ApiDeviceRegistrationRepository implements DeviceRegistrationRepository {
  ApiDeviceRegistrationRepository(this._api);

  final ApiClient _api;

  Map<String, String> _newIdempotencyKey() =>
      {'Idempotency-Key': const Uuid().v4()};

  @override
  Future<DeviceRegistration> register({
    required String installationId,
    required String platform,
    required String pushToken,
    required DeviceReport report,
  }) async =>
      DeviceRegistration.fromJson(await _api.postObject(
        '/devices',
        headers: _newIdempotencyKey(),
        data: {
          'installation_id': installationId,
          'platform': platform,
          'push_token': pushToken,
          'permission_state': report.permissionState.wireValue,
          'app_version': report.appVersion,
          'locale': report.locale,
        },
      ));

  @override
  Future<DeviceRegistration> update(
    String deviceId,
    DeviceReport report,
  ) async =>
      DeviceRegistration.fromJson(await _api.patchObject(
        '/devices/$deviceId',
        data: {
          'permission_state': report.permissionState.wireValue,
          'app_version': report.appVersion,
          'locale': report.locale,
          if (report.pushToken != null) 'push_token': report.pushToken,
        },
      ));

  @override
  Future<void> revoke(String deviceId) => _api.delete('/devices/$deviceId');

  @override
  Future<NotificationCapability> capability(String deviceId) async =>
      NotificationCapability.fromJson(
          await _api.getObject('/devices/$deviceId/notification-capability'));

  @override
  Future<PushTest> requestPushTest(
    String deviceId,
    PushPresentation presentation,
  ) async =>
      PushTest.fromJson(await _api.postObject(
        '/devices/$deviceId/push-tests',
        headers: _newIdempotencyKey(),
        data: {'expected_presentation': presentation.name},
      ));

  @override
  Future<PushTest> getPushTest(String pushTestId) async =>
      PushTest.fromJson(await _api.getObject('/push-tests/$pushTestId'));

  @override
  Future<void> confirmPushTest(PendingPushTest confirmation) async {
    await _api.postObject(
      '/push-tests/${confirmation.pushTestId}/confirm',
      headers: {'Idempotency-Key': confirmation.idempotencyKey},
      data: {
        'event': confirmation.event.wireValue,
        'occurred_at': formatUtc(confirmation.occurredAt),
      },
    );
  }
}

/// RFC 3339 en UTC con `Z` y sin fracciones de segundo.
String formatUtc(DateTime value) {
  final utc = value.toUtc();
  final withoutFraction = DateTime.utc(
    utc.year,
    utc.month,
    utc.day,
    utc.hour,
    utc.minute,
    utc.second,
  );
  return withoutFraction.toIso8601String().replaceFirst('.000', '');
}

/// Datos locales de la instalación. No guarda el token push.
abstract interface class DeviceStateStore {
  Future<String> installationId();
  Future<String?> deviceId();
  Future<void> saveDeviceId(String? value);
  Future<bool> permissionRequested();
  Future<void> markPermissionRequested();
}

class SharedPreferencesDeviceStateStore implements DeviceStateStore {
  static const _installationKey = 'gesband_installation_id';
  static const _deviceKey = 'gesband_device_id';
  static const _requestedKey = 'gesband_push_permission_requested';

  Future<SharedPreferences> get _preferences => SharedPreferences.getInstance();

  @override
  Future<String> installationId() async {
    final preferences = await _preferences;
    final current = preferences.getString(_installationKey);
    if (current != null) return current;
    final value = const Uuid().v4();
    await preferences.setString(_installationKey, value);
    return value;
  }

  @override
  Future<String?> deviceId() async =>
      (await _preferences).getString(_deviceKey);

  @override
  Future<void> saveDeviceId(String? value) async {
    final preferences = await _preferences;
    if (value == null) {
      await preferences.remove(_deviceKey);
    } else {
      await preferences.setString(_deviceKey, value);
    }
  }

  @override
  Future<bool> permissionRequested() async =>
      (await _preferences).getBool(_requestedKey) ?? false;

  @override
  Future<void> markPermissionRequested() async =>
      (await _preferences).setBool(_requestedKey, true);
}
