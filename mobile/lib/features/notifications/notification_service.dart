import 'dart:async';

import 'package:app_settings/app_settings.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../../core/api/api_client.dart';
import '../../core/localization/app_strings.dart';

enum PushPermission { unknown, notDetermined, denied, provisional, authorized }

class PushEnvelope {
  const PushEnvelope({
    required this.messageId,
    required this.data,
    this.title,
    this.body,
  });

  factory PushEnvelope.fromRemoteMessage(RemoteMessage message) => PushEnvelope(
        messageId: message.messageId,
        data: Map<String, String>.from(message.data),
        title: message.notification?.title,
        body: message.notification?.body,
      );

  final String? messageId;
  final Map<String, String> data;
  final String? title;
  final String? body;

  String? get activityId => data['activity_id'];
  String? get testChallengeId =>
      data['kind'] == 'notification_test' ? data['challenge_id'] : null;
}

abstract interface class PushGateway {
  Stream<String> get tokenChanges;
  Stream<PushEnvelope> get foregroundMessages;
  Stream<PushEnvelope> get openedMessages;

  Future<void> initialize();
  Future<PushPermission> permissionStatus();
  Future<PushPermission> requestPermission();
  Future<String?> getToken();
  Future<PushEnvelope?> getInitialMessage();
  Future<void> openSettings();
  Future<void> deleteToken();
}

class FirebasePushGateway implements PushGateway {
  FirebaseMessaging get _messaging => FirebaseMessaging.instance;

  @override
  Stream<String> get tokenChanges => _messaging.onTokenRefresh;

  @override
  Stream<PushEnvelope> get foregroundMessages =>
      FirebaseMessaging.onMessage.map(PushEnvelope.fromRemoteMessage);

  @override
  Stream<PushEnvelope> get openedMessages =>
      FirebaseMessaging.onMessageOpenedApp.map(PushEnvelope.fromRemoteMessage);

  @override
  Future<void> initialize() async {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    await _messaging.setAutoInitEnabled(true);
  }

  @override
  Future<PushPermission> permissionStatus() async => _mapPermission(
      (await _messaging.getNotificationSettings()).authorizationStatus);

  @override
  Future<PushPermission> requestPermission() async => _mapPermission(
        (await _messaging.requestPermission(
          alert: true,
          badge: true,
          sound: true,
          provisional: false,
        ))
            .authorizationStatus,
      );

  @override
  Future<String?> getToken() => _messaging.getToken();

  @override
  Future<PushEnvelope?> getInitialMessage() async {
    final message = await _messaging.getInitialMessage();
    return message == null ? null : PushEnvelope.fromRemoteMessage(message);
  }

  @override
  Future<void> openSettings() =>
      AppSettings.openAppSettings(type: AppSettingsType.notification);

  @override
  Future<void> deleteToken() => _messaging.deleteToken();

  PushPermission _mapPermission(AuthorizationStatus value) => switch (value) {
        AuthorizationStatus.notDetermined => PushPermission.notDetermined,
        AuthorizationStatus.denied => PushPermission.denied,
        AuthorizationStatus.provisional => PushPermission.provisional,
        AuthorizationStatus.authorized => PushPermission.authorized,
      };
}

class BackgroundPushStore {
  static const _key = 'pending_notification_test_challenges';

  static Future<void> record(PushEnvelope envelope) async {
    final challengeId = envelope.testChallengeId;
    if (challengeId == null) return;
    final preferences = await SharedPreferences.getInstance();
    final current = preferences.getStringList(_key) ?? <String>[];
    if (!current.contains(challengeId)) {
      await preferences.setStringList(_key, [...current, challengeId]);
    }
  }

  static Future<List<String>> takeAll() async {
    final preferences = await SharedPreferences.getInstance();
    final values = preferences.getStringList(_key) ?? const <String>[];
    await preferences.remove(_key);
    return values;
  }
}

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await BackgroundPushStore.record(PushEnvelope.fromRemoteMessage(message));
}

abstract interface class DeviceRegistrationRepository {
  Future<void> registerToken(String token);
  Future<void> unregisterToken(String token);
  Future<bool> getRegistrationStatus();
  Future<void> requestTestNotification();
  Future<void> confirmTestReceipt(String challengeId);
}

class ApiDeviceRegistrationRepository implements DeviceRegistrationRepository {
  ApiDeviceRegistrationRepository(this._api);

  final ApiClient _api;

  String get _platform => switch (defaultTargetPlatform) {
        TargetPlatform.iOS => 'ios',
        TargetPlatform.android => 'android',
        _ => 'unsupported',
      };

  Future<String> _installationId() async {
    final preferences = await SharedPreferences.getInstance();
    const key = 'gesband_installation_id';
    final current = preferences.getString(key);
    if (current != null) return current;
    final value = const Uuid().v4();
    await preferences.setString(key, value);
    return value;
  }

  @override
  Future<void> registerToken(String token) async {
    _cachedInstallationId = await _installationId();
    await _api.postObject(
      '/devices',
      data: {
        'installation_id': _cachedInstallationId,
        'push_token': token,
        'platform': _platform,
        'permission': 'granted'
      },
    );
  }

  @override
  Future<void> unregisterToken(String token) async {
    _cachedInstallationId ??= await _installationId();
    await _api
        .delete('/devices', data: {'installation_id': _cachedInstallationId});
  }

  String? _cachedInstallationId;

  @override
  Future<bool> getRegistrationStatus() async =>
      (await _api.getObject('/devices'))['active'] as bool? ?? false;

  @override
  Future<void> requestTestNotification() async {
    await _api.postObject('/devices/test');
  }

  @override
  Future<void> confirmTestReceipt(String challengeId) async {
    await _api.postObject(
      '/devices/notification-tests/$challengeId/confirm/',
    );
  }
}

class NotificationActivationState {
  const NotificationActivationState({
    this.permission = PushPermission.unknown,
    this.tokenRegistered = false,
    this.testReceiptConfirmed = false,
    this.loading = false,
    this.error,
  });

  final PushPermission permission;
  final bool tokenRegistered;
  final bool testReceiptConfirmed;
  final bool loading;
  final AppMessage? error;

  bool get fullyActive =>
      permission == PushPermission.authorized &&
      tokenRegistered &&
      testReceiptConfirmed;

  NotificationActivationState copyWith({
    PushPermission? permission,
    bool? tokenRegistered,
    bool? testReceiptConfirmed,
    bool? loading,
    AppMessage? error,
    bool clearError = false,
  }) =>
      NotificationActivationState(
        permission: permission ?? this.permission,
        tokenRegistered: tokenRegistered ?? this.tokenRegistered,
        testReceiptConfirmed: testReceiptConfirmed ?? this.testReceiptConfirmed,
        loading: loading ?? this.loading,
        error: clearError ? null : error ?? this.error,
      );
}

class NotificationController extends ChangeNotifier
    with WidgetsBindingObserver {
  NotificationController({
    required PushGateway gateway,
    required DeviceRegistrationRepository registrations,
  })  : _gateway = gateway,
        _registrations = registrations;

  final PushGateway _gateway;
  final DeviceRegistrationRepository _registrations;
  final _activityLinks = StreamController<String>.broadcast();
  final _foregroundMessages = StreamController<PushEnvelope>.broadcast();
  final List<StreamSubscription<dynamic>> _subscriptions = [];
  NotificationActivationState _state = const NotificationActivationState();
  String? _currentToken;
  bool _sessionActive = false;

  NotificationActivationState get state => _state;
  Stream<String> get activityLinks => _activityLinks.stream;
  Stream<PushEnvelope> get foregroundMessages => _foregroundMessages.stream;

  Future<void> initialize() async {
    WidgetsBinding.instance.addObserver(this);
    try {
      await _gateway.initialize();
      _subscriptions
        ..add(_gateway.tokenChanges.listen(_onTokenChanged))
        ..add(_gateway.foregroundMessages.listen(_onForegroundMessage))
        ..add(_gateway.openedMessages.listen(_onOpenedMessage));
      final initial = await _gateway.getInitialMessage();
      if (initial != null) await _handleReceipt(initial);
      final initialActivity = initial?.activityId;
      if (initialActivity != null) _activityLinks.add(initialActivity);
      for (final challenge in await BackgroundPushStore.takeAll()) {
        await _confirmReceipt(challenge);
      }
      await recheck();
    } catch (_) {
      _setState(_state.copyWith(
        loading: false,
        error: AppMessage.notificationsInitializeFailed,
      ));
    }
  }

  Future<void> bindSession() async {
    _sessionActive = true;
    await recheck();
  }

  Future<void> requestPermission() async {
    _setState(_state.copyWith(loading: true, clearError: true));
    try {
      final permission = await _gateway.requestPermission();
      _setState(_state.copyWith(permission: permission));
      await _registerCurrentToken();
    } catch (_) {
      _setState(_state.copyWith(
        error: AppMessage.notificationsPermissionFailed,
      ));
    } finally {
      _setState(_state.copyWith(loading: false));
    }
  }

  Future<void> recheck() async {
    try {
      final permission = await _gateway.permissionStatus();
      var registered = false;
      if (_sessionActive && permission == PushPermission.authorized) {
        await _registerCurrentToken();
        registered = await _registrations.getRegistrationStatus();
      }
      _setState(_state.copyWith(
        permission: permission,
        tokenRegistered: registered,
        clearError: true,
      ));
    } catch (_) {
      _setState(_state.copyWith(
        error: AppMessage.notificationsStatusFailed,
      ));
    }
  }

  Future<void> openSettings() => _gateway.openSettings();

  Future<void> sendTest() async {
    _setState(_state.copyWith(
      loading: true,
      testReceiptConfirmed: false,
      clearError: true,
    ));
    try {
      await _registrations.requestTestNotification();
    } catch (_) {
      _setState(_state.copyWith(error: AppMessage.notificationTestFailed));
    } finally {
      _setState(_state.copyWith(loading: false));
    }
  }

  Future<void> unbindSession() async {
    _sessionActive = false;
    final token = _currentToken ?? await _gateway.getToken();
    if (token != null) {
      try {
        await _registrations.unregisterToken(token);
      } catch (_) {
        // El backend revoca también los dispositivos al cerrar la sesión.
      }
    }
    await _gateway.deleteToken();
    _currentToken = null;
    _setState(const NotificationActivationState());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(recheck());
  }

  Future<void> _registerCurrentToken() async {
    if (!_sessionActive) return;
    final token = await _gateway.getToken();
    if (token == null) return;
    await _registrations.registerToken(token);
    _currentToken = token;
  }

  Future<void> _onTokenChanged(String token) async {
    if (!_sessionActive) return;
    try {
      await _registrations.registerToken(token);
      _currentToken = token;
      _setState(_state.copyWith(tokenRegistered: true, clearError: true));
    } catch (_) {
      _setState(_state.copyWith(
        tokenRegistered: false,
        error: AppMessage.deviceRegistrationRenewalFailed,
      ));
    }
  }

  Future<void> _onForegroundMessage(PushEnvelope envelope) async {
    await _handleReceipt(envelope);
    _foregroundMessages.add(envelope);
  }

  Future<void> _onOpenedMessage(PushEnvelope envelope) async {
    await _handleReceipt(envelope);
    final activityId = envelope.activityId;
    if (activityId != null) _activityLinks.add(activityId);
  }

  Future<void> _handleReceipt(PushEnvelope envelope) async {
    final challenge = envelope.testChallengeId;
    if (challenge != null) await _confirmReceipt(challenge);
  }

  Future<void> _confirmReceipt(String challenge) async {
    if (!_sessionActive) {
      await BackgroundPushStore.record(
        PushEnvelope(
          messageId: null,
          data: {'kind': 'notification_test', 'challenge_id': challenge},
        ),
      );
      return;
    }
    try {
      await _registrations.confirmTestReceipt(challenge);
      _setState(_state.copyWith(testReceiptConfirmed: true, clearError: true));
    } catch (_) {
      _setState(_state.copyWith(
        error: AppMessage.notificationConfirmationFailed,
      ));
    }
  }

  void _setState(NotificationActivationState value) {
    _state = value;
    notifyListeners();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    for (final subscription in _subscriptions) {
      unawaited(subscription.cancel());
    }
    unawaited(_activityLinks.close());
    unawaited(_foregroundMessages.close());
    super.dispose();
  }
}
