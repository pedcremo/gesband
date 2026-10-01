import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/core/storage/secure_session_store.dart';

class _NoSession implements SessionStore {
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

/// Servidor simulado: responde con una actividad o falla como sin red.
class _Server extends ApiClient {
  _Server()
      : super(baseUrl: 'http://localhost/api/v1', sessionStore: _NoSession());

  bool online = true;

  @override
  Future<Map<String, dynamic>> getObject(String path) async {
    if (!online) throw const ApiException('Error de conexión');
    return {
      'results': [
        {
          'id': 'activity-1',
          'title': 'Processó',
          'kind': 'performance',
          'status': 'published',
          'starts_at': '2099-10-04T17:00:00Z',
          'my_invitation': {'id': 'i-1', 'response': 'accepted'},
        },
      ],
    };
  }
}

void main() {
  late _Server server;
  late ApiActivitiesRepository repository;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    server = _Server();
    repository = ApiActivitiesRepository(
        server, AgendaCache(await SharedPreferences.getInstance()));
  });

  test('fresh data from the server is not marked as offline', () async {
    final agenda = await repository.listMine('band-1');

    expect(agenda.offline, isFalse);
    expect(agenda.activities.single.title, 'Processó');
  });

  test('without connection it returns the saved copy and when it was saved',
      () async {
    await repository.listMine('band-1');
    server.online = false;

    final agenda = await repository.listMine('band-1');

    expect(agenda.offline, isTrue);
    expect(agenda.cachedAt, isNotNull);
    expect(agenda.activities.single.title, 'Processó');
  });

  test('without connection and without a copy it reports the error', () async {
    server.online = false;

    expect(repository.listMine('band-1'), throwsA(isA<ApiException>()));
  });
}
