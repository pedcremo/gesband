import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

/// Evento con el que la app confirma una prueba de recepción.
enum PushTestEvent {
  receivedForeground('received_foreground'),
  openedFromBackground('opened_from_background');

  const PushTestEvent(this.wireValue);
  final String wireValue;

  static PushTestEvent? fromWire(String? value) {
    for (final item in values) {
      if (item.wireValue == value) return item;
    }
    return null;
  }
}

/// Confirmación pendiente de enviar. Guarda la clave de idempotencia para que
/// un reintento no cuente como una confirmación nueva.
class PendingPushTest {
  const PendingPushTest({
    required this.pushTestId,
    required this.event,
    required this.occurredAt,
    required this.idempotencyKey,
  });

  factory PendingPushTest.openedFromBackground(
    String pushTestId, {
    required DateTime occurredAt,
  }) =>
      PendingPushTest(
        pushTestId: pushTestId,
        event: PushTestEvent.openedFromBackground,
        occurredAt: occurredAt.toUtc(),
        idempotencyKey: const Uuid().v4(),
      );

  factory PendingPushTest.receivedForeground(
    String pushTestId, {
    required DateTime occurredAt,
  }) =>
      PendingPushTest(
        pushTestId: pushTestId,
        event: PushTestEvent.receivedForeground,
        occurredAt: occurredAt.toUtc(),
        idempotencyKey: const Uuid().v4(),
      );

  static PendingPushTest? tryParse(String raw) {
    try {
      final json = jsonDecode(raw) as Map<String, dynamic>;
      final event = PushTestEvent.fromWire(json['event'] as String?);
      final at = DateTime.tryParse(json['occurred_at'] as String? ?? '');
      final id = json['push_test_id'] as String?;
      final key = json['idempotency_key'] as String?;
      if (event == null || at == null || id == null || key == null) {
        return null;
      }
      return PendingPushTest(
        pushTestId: id,
        event: event,
        occurredAt: at.toUtc(),
        idempotencyKey: key,
      );
    } on FormatException {
      return null;
    } on TypeError {
      return null;
    }
  }

  final String pushTestId;
  final PushTestEvent event;
  final DateTime occurredAt;
  final String idempotencyKey;

  String encode() => jsonEncode({
        'push_test_id': pushTestId,
        'event': event.wireValue,
        'occurred_at': occurredAt.toUtc().toIso8601String(),
        'idempotency_key': idempotencyKey,
      });
}

/// Confirmaciones de pruebas que no se pudieron enviar todavía: llegaron en
/// segundo plano, sin sesión o sin red. Solo contiene identificadores opacos de
/// prueba, nunca tokens ni contenido de avisos.
abstract interface class PendingPushTestStore {
  factory PendingPushTestStore.shared() = SharedPreferencesPendingPushTestStore;

  Future<void> add(PendingPushTest value);
  Future<List<PendingPushTest>> all();
  Future<void> remove(String pushTestId);
  Future<void> clear();
}

class SharedPreferencesPendingPushTestStore implements PendingPushTestStore {
  static const _key = 'pending_push_test_confirmations';

  Future<SharedPreferences> _preferences() async {
    final preferences = await SharedPreferences.getInstance();
    // El manejador de segundo plano escribe desde otro isolate: hay que
    // releer el disco para no trabajar con una copia antigua.
    await preferences.reload();
    return preferences;
  }

  @override
  Future<void> add(PendingPushTest value) async {
    final preferences = await _preferences();
    final current = preferences.getStringList(_key) ?? const <String>[];
    final kept = current.where(
        (raw) => PendingPushTest.tryParse(raw)?.pushTestId != value.pushTestId);
    await preferences.setStringList(_key, [...kept, value.encode()]);
  }

  @override
  Future<List<PendingPushTest>> all() async {
    final preferences = await _preferences();
    return [
      for (final raw in preferences.getStringList(_key) ?? const <String>[])
        if (PendingPushTest.tryParse(raw) case final PendingPushTest value)
          value,
    ];
  }

  @override
  Future<void> remove(String pushTestId) async {
    final preferences = await _preferences();
    final current = preferences.getStringList(_key) ?? const <String>[];
    await preferences.setStringList(_key, [
      for (final raw in current)
        if (PendingPushTest.tryParse(raw)?.pushTestId != pushTestId) raw,
    ]);
  }

  @override
  Future<void> clear() async {
    final preferences = await _preferences();
    await preferences.remove(_key);
  }
}
