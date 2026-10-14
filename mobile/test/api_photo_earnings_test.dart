import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/core/storage/secure_session_store.dart';

import 'support/earnings_fixtures.dart';
import 'support/visual_harness.dart';

class _NoSession implements SessionStore {
  @override
  Future<SessionTokens?> readTokens() async => null;

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

/// Servidor falso: guarda cada petición y responde lo que se le indique.
class _Server implements HttpClientAdapter {
  final requests = <(RequestOptions, String)>[];
  final responses = <(int, Object?)>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final body = requestStream == null
        ? ''
        : latin1.decode(await requestStream.expand((chunk) => chunk).toList());
    requests.add((options, body));
    final (status, data) = responses.removeAt(0);
    return ResponseBody.fromString(
      data == null ? '' : jsonEncode(data),
      status,
      headers: {
        Headers.contentTypeHeader: [
          status >= 400 ? 'application/problem+json' : 'application/json'
        ],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

(ApiClient, _Server) _client() {
  final server = _Server();
  final dio = Dio(BaseOptions(baseUrl: 'https://gesband.example.test/api/v1'))
    ..httpClientAdapter = server;
  final api = ApiClient(
      baseUrl: 'https://gesband.example.test/api/v1',
      sessionStore: _NoSession(),
      dio: dio)
    ..selectAssociation('band-1');
  return (api, server);
}

final _jpeg = Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0, 1, 2, 3]);

void main() {
  group('server error messages', () {
    test('reads the field errors of problem+json', () {
      expect(
        ApiClient.serverMessageOf({
          'type': 'https://docs.example.invalid/problems/validation',
          'title': 'Datos no válidos',
          'status': 422,
          'code': 'validation.failed',
          'trace_id': 'trace-synthetic-004',
          'errors': [
            {
              'field': 'photo',
              'code': 'invalid_image',
              'message': 'El archivo no es una imagen válida.'
            }
          ],
        }),
        'El archivo no es una imagen válida.',
      );
    });

    test('reads the default DRF shapes', () {
      expect(
          ApiClient.serverMessageOf({
            'photo': ['La imagen supera 5 MB.']
          }),
          'La imagen supera 5 MB.');
      expect(ApiClient.serverMessageOf({'detail': 'No encontrado.'}),
          'No encontrado.');
      expect(ApiClient.serverMessageOf(['No hay una ficha vinculada.']),
          'No hay una ficha vinculada.');
      expect(ApiClient.serverMessageOf({'message': 'Mensaje'}), 'Mensaje');
    });

    test('returns null when there is nothing readable', () {
      expect(ApiClient.serverMessageOf(null), isNull);
      expect(ApiClient.serverMessageOf('<html>413</html>'), isNull);
      expect(
          ApiClient.serverMessageOf({
            'type': 'about:blank',
            'title': 'Error',
            'status': 500,
            'code': 'server.error',
            'trace_id': 't',
          }),
          isNull);
    });
  });

  group('own photo', () {
    // Regresión: la subida usaba POST y el servidor solo acepta PUT.
    test('is uploaded with PUT as multipart field photo', () async {
      final (api, server) = _client();
      server.responses.add((
        200,
        {
          ...memberJson(),
          'photo_url':
              'https://gesband.example.test/api/v1/members/member-1/photo/',
        }
      ));

      final profile = await ApiProfileRepository(api)
          .updatePhoto('band-1', _jpeg, filename: 'image_picker_1.jpg');

      final (request, body) = server.requests.single;
      expect(request.method, 'PUT');
      expect(request.path, '/members/me/photo/?association_id=band-1');
      expect(request.headers['X-Association-ID'], 'band-1');
      expect(request.contentType, startsWith('multipart/form-data'));
      expect(body, contains('name="photo"; filename="image_picker_1.jpg"'));
      expect(body, contains('content-type: image/jpeg'));
      expect(profile.photoUrl, endsWith('/members/member-1/photo/'));
    });

    test('a validation error keeps the server message', () async {
      final (api, server) = _client();
      server.responses.add((
        400,
        {
          'photo': ['El archivo no es una imagen válida.']
        }
      ));

      await expectLater(
        ApiProfileRepository(api)
            .updatePhoto('band-1', _jpeg, filename: 'x.jpg'),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 400)
            .having((e) => e.fromServer, 'fromServer', isTrue)
            .having((e) => e.message, 'message',
                'El archivo no es una imagen válida.')),
      );
    });

    test('an error without a body uses the generic message', () async {
      final (api, server) = _client();
      server.responses.add((413, null));

      await expectLater(
        ApiProfileRepository(api)
            .updatePhoto('band-1', _jpeg, filename: 'x.jpg'),
        throwsA(isA<ApiException>()
            .having((e) => e.fromServer, 'fromServer', isFalse)),
      );
    });

    test('is deleted and the profile is reloaded for the same band', () async {
      final (api, server) = _client();
      server.responses
        ..add((204, null))
        ..add((200, memberJson()));

      final profile = await ApiProfileRepository(api).deletePhoto('band-1');

      expect(server.requests.map((r) => '${r.$1.method} ${r.$1.path}'), [
        'DELETE /members/me/photo/?association_id=band-1',
        'GET /members/me/?association_id=band-1',
      ]);
      expect(profile.photoUrl, isNull);
    });
  });

  test('earnings come from /members/me/earnings', () async {
    final (api, server) = _client();
    server.responses.add((200, earningsContractJson()));

    final earnings = await ApiProfileRepository(api).getEarnings('band-1');

    final (request, _) = server.requests.single;
    expect(request.method, 'GET');
    expect(request.path, '/members/me/earnings/?association_id=band-1');
    expect(request.headers['X-Association-ID'], 'band-1');
    expect(earnings.owedTotal, const Money(5000));
  });
}
