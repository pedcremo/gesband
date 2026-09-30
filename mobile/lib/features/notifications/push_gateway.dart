import 'dart:async';

import 'package:app_settings/app_settings.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'pending_push_tests.dart';

/// Estado del permiso tal como lo observa la app. Los valores coinciden con
/// `PermissionState` del contrato mediante [wireValue].
enum PushPermission {
  notDetermined('not_determined'),
  provisional('provisional'),
  granted('granted'),
  denied('denied'),
  restricted('restricted'),
  unknown('unknown');

  const PushPermission(this.wireValue);

  final String wireValue;

  static PushPermission fromWire(String? value) => PushPermission.values
      .firstWhere((item) => item.wireValue == value, orElse: () => unknown);
}

/// Datos de un mensaje push. El servidor envía todos los valores como texto.
class PushEnvelope {
  const PushEnvelope({
    required this.messageId,
    required this.data,
    this.title,
    this.body,
  });

  factory PushEnvelope.fromRemoteMessage(RemoteMessage message) => PushEnvelope(
        messageId: message.messageId,
        data: {
          for (final entry in message.data.entries) entry.key: '${entry.value}',
        },
        title: message.notification?.title,
        body: message.notification?.body,
      );

  static const testKind = 'notification_test';

  final String? messageId;
  final Map<String, String> data;
  final String? title;
  final String? body;

  String? get kind => data['kind'];
  String? get notificationId => _nonEmpty('notification_id');
  String? get activityId => _nonEmpty('activity_id');
  String? get pollId => _nonEmpty('poll_id');

  /// Identificador de la prueba de recepción, solo en mensajes de prueba.
  String? get pushTestId => kind == testKind ? _nonEmpty('push_test_id') : null;

  bool get isTest => kind == testKind;

  /// Pantalla que debe abrirse al pulsar el aviso. `kind` decide cuando el
  /// mensaje trae ambos identificadores.
  NotificationTarget? get target {
    if (isTest) return null;
    final poll = pollId;
    final activity = activityId;
    if (kind == 'poll' && poll != null) return PollTarget(poll);
    if (activity != null) return ActivityTarget(activity);
    if (poll != null) return PollTarget(poll);
    return null;
  }

  String? _nonEmpty(String key) {
    final value = data[key];
    return value == null || value.isEmpty ? null : value;
  }
}

sealed class NotificationTarget {
  const NotificationTarget(this.id);
  final String id;
}

final class ActivityTarget extends NotificationTarget {
  const ActivityTarget(super.id);

  @override
  bool operator ==(Object other) => other is ActivityTarget && other.id == id;

  @override
  int get hashCode => Object.hash(ActivityTarget, id);
}

final class PollTarget extends NotificationTarget {
  const PollTarget(super.id);

  @override
  bool operator ==(Object other) => other is PollTarget && other.id == id;

  @override
  int get hashCode => Object.hash(PollTarget, id);
}

/// Acceso al proveedor push. Permite sustituir Firebase en las pruebas.
abstract interface class PushGateway {
  /// `android` o `ios`, como espera el contrato.
  String get platform;
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
  String get platform =>
      defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';

  @override
  Stream<String> get tokenChanges => _messaging.onTokenRefresh;

  @override
  Stream<PushEnvelope> get foregroundMessages =>
      FirebaseMessaging.onMessage.map(PushEnvelope.fromRemoteMessage);

  @override
  Stream<PushEnvelope> get openedMessages =>
      FirebaseMessaging.onMessageOpenedApp.map(PushEnvelope.fromRemoteMessage);

  /// Falla si faltan `google-services.json` o `GoogleService-Info.plist`; el
  /// controlador lo trata como servicio no disponible.
  @override
  Future<void> initialize() async {
    await Firebase.initializeApp();
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    await _messaging.setAutoInitEnabled(true);
    // En iOS, sin esto el sistema no muestra los avisos en primer plano; la
    // app los presenta con su propio SnackBar, así que se desactiva el banner.
    await _messaging.setForegroundNotificationPresentationOptions(
      alert: false,
      badge: true,
      sound: false,
    );
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
  Future<String?> getToken() async {
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      // Sin token APNs, getToken() lanza una excepción en iOS. Puede tardar
      // unos segundos tras el primer arranque; se reintentará al volver.
      final apns = await _messaging.getAPNSToken();
      if (apns == null) return null;
    }
    return _messaging.getToken();
  }

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
        AuthorizationStatus.authorized => PushPermission.granted,
      };
}

/// Se ejecuta en un isolate aparte, sin sesión ni interfaz. Solo anota las
/// pruebas de recepción para confirmarlas al abrir la app.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  final envelope = PushEnvelope.fromRemoteMessage(message);
  final pushTestId = envelope.pushTestId;
  if (pushTestId == null) return;
  await PendingPushTestStore.shared().add(PendingPushTest.openedFromBackground(
    pushTestId,
    occurredAt: DateTime.now().toUtc(),
  ));
}
