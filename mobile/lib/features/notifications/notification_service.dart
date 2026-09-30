import 'dart:async';

import 'package:flutter/widgets.dart';

import '../../core/api/api_client.dart';
import '../../core/localization/app_strings.dart';
import 'device_registration.dart';
import 'pending_push_tests.dart';
import 'push_gateway.dart';

export 'device_registration.dart';
export 'pending_push_tests.dart';
export 'push_gateway.dart';

const Object _unset = Object();

/// Estado del paso de activación (MUST-NOTIF-01). Permiso, registro y
/// recepción se muestran por separado: ninguno implica los otros.
class NotificationActivationState {
  const NotificationActivationState({
    this.available = true,
    this.permission = PushPermission.unknown,
    this.tokenRegistered = false,
    this.receiptConfirmed = false,
    this.lastReceiptConfirmedAt,
    this.serverAction,
    this.lastTest,
    this.loading = false,
    this.error,
  });

  /// Falso si Firebase no se pudo iniciar (p. ej. sin ficheros de
  /// configuración). La app sigue siendo usable sin avisos push.
  final bool available;

  /// Permiso observado en el sistema, el mismo que se envía al servidor.
  final PushPermission permission;
  final bool tokenRegistered;
  final bool receiptConfirmed;
  final DateTime? lastReceiptConfirmedAt;

  /// `action_required` devuelto por el servidor, si se pudo consultar.
  final NotificationAction? serverAction;
  final PushTest? lastTest;
  final bool loading;
  final AppMessage? error;

  /// Paso que debe ver la persona. Se usa el del servidor y, si no hay
  /// respuesta, se deduce del estado local con el mismo criterio.
  NotificationAction get nextAction {
    if (!available) return NotificationAction.none;
    final server = serverAction;
    if (server != null) return server;
    return switch (permission) {
      PushPermission.notDetermined ||
      PushPermission.unknown =>
        NotificationAction.requestSystemPermission,
      PushPermission.denied ||
      PushPermission.restricted =>
        NotificationAction.openSystemSettings,
      _ when !tokenRegistered => NotificationAction.registerToken,
      _ when !receiptConfirmed => NotificationAction.runReceiveTest,
      _ => NotificationAction.none,
    };
  }

  bool get fullyActive =>
      available &&
      permission == PushPermission.granted &&
      tokenRegistered &&
      receiptConfirmed;

  NotificationActivationState copyWith({
    bool? available,
    PushPermission? permission,
    bool? tokenRegistered,
    bool? receiptConfirmed,
    Object? lastReceiptConfirmedAt = _unset,
    Object? serverAction = _unset,
    Object? lastTest = _unset,
    bool? loading,
    Object? error = _unset,
  }) =>
      NotificationActivationState(
        available: available ?? this.available,
        permission: permission ?? this.permission,
        tokenRegistered: tokenRegistered ?? this.tokenRegistered,
        receiptConfirmed: receiptConfirmed ?? this.receiptConfirmed,
        lastReceiptConfirmedAt: identical(lastReceiptConfirmedAt, _unset)
            ? this.lastReceiptConfirmedAt
            : lastReceiptConfirmedAt as DateTime?,
        serverAction: identical(serverAction, _unset)
            ? this.serverAction
            : serverAction as NotificationAction?,
        lastTest:
            identical(lastTest, _unset) ? this.lastTest : lastTest as PushTest?,
        loading: loading ?? this.loading,
        error: identical(error, _unset) ? this.error : error as AppMessage?,
      );
}

/// Coordina permiso, registro del dispositivo, pruebas de recepción y
/// apertura de avisos. Nunca escribe tokens ni contenido de avisos en logs.
class NotificationController extends ChangeNotifier
    with WidgetsBindingObserver {
  NotificationController({
    required PushGateway gateway,
    required DeviceRegistrationRepository registrations,
    required DeviceStateStore deviceStore,
    required PendingPushTestStore pendingTests,
    required String appVersion,
    String languageCode = 'es',
    DateTime Function()? clock,
  })  : _gateway = gateway,
        _registrations = registrations,
        _deviceStore = deviceStore,
        _pendingTests = pendingTests,
        _appVersion = appVersion,
        _locale = deviceLocaleTag(languageCode),
        _clock = clock ?? DateTime.now;

  final PushGateway _gateway;
  final DeviceRegistrationRepository _registrations;
  final DeviceStateStore _deviceStore;
  final PendingPushTestStore _pendingTests;
  final String _appVersion;
  final DateTime Function() _clock;
  String _locale;

  final _targets = StreamController<NotificationTarget>.broadcast();
  final _foregroundMessages = StreamController<PushEnvelope>.broadcast();
  final _deactivations = StreamController<void>.broadcast();
  final List<StreamSubscription<dynamic>> _subscriptions = [];
  final Set<String> _confirmedTests = {};

  NotificationActivationState _state = const NotificationActivationState();
  bool _sessionActive = false;
  bool _observing = false;
  String? _lastSentToken;
  Future<void>? _syncing;
  bool _syncAgain = false;

  NotificationActivationState get state => _state;

  /// Actividad o encuesta que debe abrirse tras pulsar un aviso.
  Stream<NotificationTarget> get targets => _targets.stream;

  /// Avisos recibidos con la app en primer plano.
  Stream<PushEnvelope> get foregroundMessages => _foregroundMessages.stream;

  /// Se emite al detectar que un permiso concedido se ha retirado.
  Stream<void> get deactivations => _deactivations.stream;

  Future<void> initialize() async {
    if (!_observing) {
      WidgetsBinding.instance.addObserver(this);
      _observing = true;
    }
    try {
      await _gateway.initialize();
    } catch (_) {
      _setState(_state.copyWith(
        available: false,
        loading: false,
        error: AppMessage.notificationsInitializeFailed,
      ));
      return;
    }
    _subscriptions
      ..add(_gateway.tokenChanges.listen(_onTokenChanged))
      ..add(_gateway.foregroundMessages.listen(_onForegroundMessage))
      ..add(_gateway.openedMessages.listen(_onOpenedMessage));
    try {
      final initial = await _gateway.getInitialMessage();
      if (initial != null) await _onOpenedMessage(initial);
    } catch (_) {
      // Sin mensaje inicial legible no hay nada que abrir.
    }
    await refresh();
  }

  /// Llamar tras iniciar sesión o al arrancar con una sesión guardada.
  Future<void> bindSession() async {
    _sessionActive = true;
    await refresh();
    await _flushPendingTests();
  }

  /// Revoca el dispositivo y borra el token para que los avisos de esta
  /// persona no lleguen a la siguiente sesión. Llamar antes de cerrar la
  /// sesión en el servidor, porque la revocación necesita autenticación.
  Future<void> unbindSession() async {
    _sessionActive = false;
    final deviceId = await _deviceStore.deviceId();
    if (deviceId != null) {
      try {
        await _registrations.revoke(deviceId);
      } catch (_) {
        // El servidor también revoca los dispositivos al cerrar la sesión.
      }
    }
    if (_state.available) {
      try {
        await _gateway.deleteToken();
      } catch (_) {
        // Sin red no se puede invalidar el token; el servidor ya lo revocó.
      }
    }
    await _deviceStore.saveDeviceId(null);
    await _pendingTests.clear();
    _lastSentToken = null;
    _confirmedTests.clear();
    _setState(NotificationActivationState(
      available: _state.available,
      permission: _state.permission,
      error: _state.available ? null : _state.error,
    ));
  }

  Future<void> requestPermission() async {
    if (!_state.available) return;
    _setState(_state.copyWith(loading: true, error: null));
    try {
      await _deviceStore.markPermissionRequested();
      await _gateway.requestPermission();
    } catch (_) {
      _setState(_state.copyWith(
        error: AppMessage.notificationsPermissionFailed,
      ));
    }
    await refresh();
    _setState(_state.copyWith(loading: false));
  }

  Future<void> openSettings() async {
    try {
      await _gateway.openSettings();
    } catch (_) {
      // Si no se puede abrir, la pantalla sigue mostrando el paso pendiente.
    }
  }

  /// Relee el permiso, informa al servidor y consulta el paso siguiente.
  /// Las llamadas simultáneas se agrupan en una sola sincronización.
  Future<void> refresh() {
    final running = _syncing;
    if (running != null) {
      _syncAgain = true;
      return running;
    }
    final future = _runSync();
    _syncing = future;
    return future;
  }

  Future<void> setLanguage(String languageCode) async {
    final tag = deviceLocaleTag(languageCode);
    if (tag == _locale) return;
    _locale = tag;
    if (_sessionActive) await refresh();
  }

  Future<void> sendTest(PushPresentation presentation) async {
    if (!_state.available || !_sessionActive) return;
    _setState(_state.copyWith(loading: true, error: null));
    try {
      var deviceId = await _deviceStore.deviceId();
      if (deviceId == null) {
        await refresh();
        deviceId = await _deviceStore.deviceId();
      }
      if (deviceId == null) {
        _setState(_state.copyWith(error: AppMessage.deviceRegistrationFailed));
        return;
      }
      final test = await _registrations.requestPushTest(deviceId, presentation);
      _setState(_state.copyWith(lastTest: test));
    } catch (_) {
      _setState(_state.copyWith(error: AppMessage.notificationTestFailed));
    } finally {
      _setState(_state.copyWith(loading: false));
    }
  }

  /// Consulta el estado de la última prueba (p. ej. `provider_failed`).
  Future<void> refreshTest() async {
    final test = _state.lastTest;
    if (test == null || !_sessionActive) return;
    try {
      _setState(_state.copyWith(
        lastTest: await _registrations.getPushTest(test.id),
      ));
    } catch (_) {
      _setState(_state.copyWith(error: AppMessage.notificationsStatusFailed));
    }
    await refresh();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) return;
    unawaited(() async {
      await refresh();
      await _flushPendingTests();
    }());
  }

  Future<void> _runSync() async {
    try {
      do {
        _syncAgain = false;
        await _syncNow();
      } while (_syncAgain);
    } finally {
      _syncing = null;
    }
  }

  Future<void> _syncNow() async {
    if (!_state.available) return;
    final previous = _state.permission;
    final permission = await _observePermission();
    final lost = _isEnabled(previous) && !_isEnabled(permission);
    _setState(_state.copyWith(permission: permission));
    if (lost) _deactivations.add(null);
    if (!_sessionActive) return;

    try {
      final token = await _readToken();
      final registration = await _reportDevice(permission, token);
      if (registration == null) {
        _setState(_state.copyWith(
          tokenRegistered: false,
          serverAction: NotificationAction.registerToken,
          error: AppMessage.deviceRegistrationFailed,
        ));
        return;
      }
      final capability = await _registrations.capability(registration.id);
      _setState(_state.copyWith(
        tokenRegistered: capability.tokenRegistered,
        receiptConfirmed: capability.receiptConfirmed,
        lastReceiptConfirmedAt: capability.lastReceiptConfirmedAt,
        serverAction: capability.actionRequired,
        error: null,
      ));
    } catch (_) {
      _setState(_state.copyWith(
        serverAction: null,
        error: AppMessage.notificationsStatusFailed,
      ));
    }
  }

  /// Android no distingue «sin preguntar» de «denegado»: antes de la primera
  /// solicitud desde esta instalación se trata como no determinado para
  /// ofrecer la solicitud; después, como denegado, para enviar a ajustes en
  /// lugar de repetir una solicitud que el sistema ya no muestra.
  Future<PushPermission> _observePermission() async {
    try {
      final raw = await _gateway.permissionStatus();
      if (raw == PushPermission.denied &&
          !await _deviceStore.permissionRequested()) {
        return PushPermission.notDetermined;
      }
      return raw;
    } catch (_) {
      return PushPermission.unknown;
    }
  }

  bool _isEnabled(PushPermission value) =>
      value == PushPermission.granted || value == PushPermission.provisional;

  Future<String?> _readToken() async {
    try {
      return await _gateway.getToken();
    } catch (_) {
      return null;
    }
  }

  /// Registra o actualiza el dispositivo. Devuelve null si no hay registro
  /// posible todavía (sin token y sin registro previo).
  Future<DeviceRegistration?> _reportDevice(
    PushPermission permission,
    String? token,
  ) async {
    final deviceId = await _deviceStore.deviceId();
    if (deviceId != null) {
      final changedToken = token != null && token != _lastSentToken;
      try {
        final updated = await _registrations.update(
          deviceId,
          _report(permission, changedToken ? token : null),
        );
        if (changedToken) _lastSentToken = token;
        if (updated.active) return updated;
      } on ApiException catch (error) {
        if (error.statusCode != 404) rethrow;
      }
      // El servidor ya no reconoce el registro: se crea de nuevo.
      await _deviceStore.saveDeviceId(null);
    }
    if (token == null) return null;
    final created = await _registrations.register(
      installationId: await _deviceStore.installationId(),
      platform: _gateway.platform,
      pushToken: token,
      report: _report(permission, token),
    );
    await _deviceStore.saveDeviceId(created.id);
    _lastSentToken = token;
    return created;
  }

  DeviceReport _report(PushPermission permission, String? token) =>
      DeviceReport(
        permissionState: permission,
        appVersion: _appVersion,
        locale: _locale,
        pushToken: token,
      );

  Future<void> _onTokenChanged(String token) async {
    if (!_sessionActive) return;
    try {
      final deviceId = await _deviceStore.deviceId();
      if (deviceId == null) {
        await refresh();
        return;
      }
      await _registrations.update(
        deviceId,
        _report(_state.permission, token),
      );
      _lastSentToken = token;
      await refresh();
    } catch (_) {
      _setState(_state.copyWith(
        tokenRegistered: false,
        error: AppMessage.deviceRegistrationRenewalFailed,
      ));
    }
  }

  Future<void> _onForegroundMessage(PushEnvelope envelope) async {
    if (envelope.isTest) {
      await _recordTestReceipt(envelope, PushTestEvent.receivedForeground);
    }
    if (_sessionActive) _foregroundMessages.add(envelope);
  }

  Future<void> _onOpenedMessage(PushEnvelope envelope) async {
    if (envelope.isTest) {
      await _recordTestReceipt(envelope, PushTestEvent.openedFromBackground);
      return;
    }
    final target = envelope.target;
    if (target != null) _targets.add(target);
  }

  Future<void> _recordTestReceipt(
    PushEnvelope envelope,
    PushTestEvent event,
  ) async {
    final id = envelope.pushTestId;
    if (id == null || _confirmedTests.contains(id)) return;
    final now = _clock();
    await _pendingTests.add(switch (event) {
      PushTestEvent.receivedForeground =>
        PendingPushTest.receivedForeground(id, occurredAt: now),
      PushTestEvent.openedFromBackground =>
        PendingPushTest.openedFromBackground(id, occurredAt: now),
    });
    await _flushPendingTests();
  }

  /// Envía las confirmaciones pendientes. Las que fallan por red se quedan
  /// para el siguiente intento; las rechazadas definitivamente se descartan.
  Future<void> _flushPendingTests() async {
    if (!_sessionActive || !_state.available) return;
    var confirmed = false;
    for (final pending in await _pendingTests.all()) {
      if (_confirmedTests.contains(pending.pushTestId)) {
        await _pendingTests.remove(pending.pushTestId);
        continue;
      }
      try {
        await _registrations.confirmPushTest(pending);
        _confirmedTests.add(pending.pushTestId);
        await _pendingTests.remove(pending.pushTestId);
        confirmed = true;
        final test = _state.lastTest;
        if (test != null && test.id == pending.pushTestId) {
          _setState(_state.copyWith(
            lastTest: test.withStatus(
              pending.event == PushTestEvent.receivedForeground
                  ? PushTestStatus.receivedForeground
                  : PushTestStatus.openedFromBackground,
            ),
          ));
        }
      } on ApiException catch (error) {
        final status = error.statusCode;
        if (status != null && status >= 400 && status < 500) {
          // 404/409/422: la prueba no es de esta sesión, caducó o ya constaba.
          await _pendingTests.remove(pending.pushTestId);
        } else {
          _setState(_state.copyWith(
            error: AppMessage.notificationConfirmationFailed,
          ));
        }
      } catch (_) {
        _setState(_state.copyWith(
          error: AppMessage.notificationConfirmationFailed,
        ));
      }
    }
    if (confirmed) {
      _setState(_state.copyWith(receiptConfirmed: true));
      await refresh();
    }
  }

  void _setState(NotificationActivationState value) {
    _state = value;
    notifyListeners();
  }

  @override
  void dispose() {
    if (_observing) WidgetsBinding.instance.removeObserver(this);
    for (final subscription in _subscriptions) {
      unawaited(subscription.cancel());
    }
    unawaited(_targets.close());
    unawaited(_foregroundMessages.close());
    unawaited(_deactivations.close());
    super.dispose();
  }
}
