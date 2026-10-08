import 'package:flutter_test/flutter_test.dart';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/core/storage/secure_session_store.dart';

class _NoSession implements SessionStore {
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

class _Recorder extends ApiClient {
  _Recorder()
      : super(
            baseUrl: 'https://gesband.example.test/api/v1',
            sessionStore: _NoSession());

  final paths = <String>[];

  @override
  Future<Map<String, dynamic>> getObject(String path) async {
    paths.add(path);
    return {
      'id': 'member-1',
      'first_name': 'Marta',
      'last_name': 'Prova',
      'instruments': const [],
    };
  }
}

void main() {
  final api = ApiClient(
      baseUrl: 'https://gesband.example.test/api/v1',
      sessionStore: _NoSession());

  test('protected files are requested relative to the API', () {
    expect(
      api.apiPathFor(
          'https://gesband.example.test/api/v1/associations/3f0c/logo/'),
      '/associations/3f0c/logo/',
    );
    expect(api.apiPathFor('/api/v1/members/m-1/photo/?v=2'),
        '/members/m-1/photo/?v=2');
  });

  test('the session token is never sent to another host or path', () {
    expect(api.apiPathFor('https://otro.example.test/api/v1/x/logo/'), isNull);
    expect(
        api.apiPathFor('https://gesband.example.test/media/logo.png'), isNull);
    expect(api.apiPathFor('https://gesband.example.test/api/v10/x'), isNull);
  });

  // Regresión: la ficha propia se pedía a `/members/`, que es el censo.
  test('the own profile comes from /members/me/', () async {
    final recorder = _Recorder();
    final profile = await ApiProfileRepository(recorder).getMine('band-1');

    expect(recorder.paths, ['/members/me/?association_id=band-1']);
    expect(profile.fullName, 'Marta Prova');
  });
}
