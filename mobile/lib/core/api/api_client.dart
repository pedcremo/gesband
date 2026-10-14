import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../storage/secure_session_store.dart';

class ApiException implements Exception {
  const ApiException(
    this.message, {
    this.statusCode,
    this.code,
    this.fromServer = false,
  });

  final String message;
  final int? statusCode;
  final String? code;

  /// `message` es el texto que envió el servidor (ya en el idioma pedido con
  /// `Accept-Language`) y no el genérico de la app.
  final bool fromServer;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({
    required String baseUrl,
    required SessionStore sessionStore,
    Dio? dio,
  })  : _sessionStore = sessionStore,
        _dio = dio ??
            Dio(
              BaseOptions(
                baseUrl: baseUrl,
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 20),
                headers: const {'Accept': 'application/json'},
              ),
            ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          options.headers['Accept-Language'] = _languageCode;
          final tokens = await _sessionStore.readTokens();
          if (tokens != null) {
            options.headers['Authorization'] = 'Bearer ${tokens.accessToken}';
          }
          if (_associationId != null) {
            options.headers['X-Association-ID'] = _associationId;
          }
          handler.next(options);
        },
        onError: (error, handler) {
          final data = error.response?.data;
          final body = data is Map<String, dynamic> ? data : null;
          final message = serverMessageOf(data);
          handler.reject(
            DioException(
              requestOptions: error.requestOptions,
              response: error.response,
              error: ApiException(
                message ?? 'No se pudo completar la petición',
                statusCode: error.response?.statusCode,
                code: body?['code'] as String?,
                fromServer: message != null,
              ),
            ),
          );
        },
      ),
    );
  }

  /// Primer texto legible de un error del API. Admite el `problem+json` del
  /// contrato (`detail` y `errors[].message`), `message`, y la forma por
  /// defecto de DRF (`{"photo": ["..."]}`, `["..."]`).
  static String? serverMessageOf(Object? data) {
    String? first(Object? value) => switch (value) {
          String() when value.trim().isNotEmpty => value.trim(),
          List() => value.map(first).nonNulls.firstOrNull,
          Map() => first(value['message']) ??
              value.values.map(first).nonNulls.firstOrNull,
          _ => null,
        };
    if (data is Map<String, dynamic>) {
      return first(data['message']) ??
          first(data['errors']) ??
          first(data['detail']) ??
          first(data['non_field_errors']) ??
          first({
            for (final entry in data.entries)
              if (!_problemMembers.contains(entry.key)) entry.key: entry.value,
          });
    }
    return first(data is List ? data : null);
  }

  /// Miembros de `problem+json` que no son el mensaje para la persona.
  static const _problemMembers = {
    'type',
    'title',
    'status',
    'code',
    'trace_id',
    'instance',
  };

  final Dio _dio;
  final SessionStore _sessionStore;
  String? _associationId;
  String _languageCode = 'es';

  void selectAssociation(String? associationId) {
    _associationId = associationId;
  }

  void selectLanguage(String languageCode) {
    _languageCode = languageCode;
  }

  Future<Map<String, dynamic>> getObject(String path) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(path);
      return response.data ?? const {};
    } on DioException catch (error) {
      throw error.error is ApiException
          ? error.error! as ApiException
          : const ApiException('Error de conexión');
    }
  }

  Future<List<Map<String, dynamic>>> getList(String path) async {
    final body = await getObject(path);
    final values = body['results'] as List<dynamic>? ?? const [];
    return values.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> postObject(
    String path, {
    Object? data,
    Map<String, String>? headers,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        path,
        data: data,
        options: headers == null ? null : Options(headers: headers),
      );
      return response.data ?? const {};
    } on DioException catch (error) {
      throw error.error is ApiException
          ? error.error! as ApiException
          : const ApiException('Error de conexión');
    }
  }

  Future<Map<String, dynamic>> patchObject(
    String path, {
    Object? data,
    Map<String, String>? headers,
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(
        path,
        data: data,
        options: headers == null ? null : Options(headers: headers),
      );
      return response.data ?? const {};
    } on DioException catch (error) {
      throw error.error is ApiException
          ? error.error! as ApiException
          : const ApiException('Error de conexión');
    }
  }

  Future<Map<String, dynamic>> putObject(
    String path, {
    Object? data,
  }) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(path, data: data);
      return response.data ?? const {};
    } on DioException catch (error) {
      throw error.error is ApiException
          ? error.error! as ApiException
          : const ApiException('Error de conexión');
    }
  }

  Future<void> delete(String path, {Object? data}) async {
    try {
      await _dio.delete<void>(path, data: data);
    } on DioException catch (error) {
      throw error.error is ApiException
          ? error.error! as ApiException
          : const ApiException('Error de conexión');
    }
  }

  /// Ruta relativa al API para una URL absoluta que envía el servidor
  /// (logotipo, foto). Solo se aceptan rutas del mismo host bajo el prefijo
  /// del API, y la petición sale siempre contra la base configurada: el
  /// token nunca se manda a otro sitio.
  String? apiPathFor(String url) {
    final target = Uri.tryParse(url);
    final base = Uri.parse(_dio.options.baseUrl);
    if (target == null) return null;
    final prefix = base.path.endsWith('/') ? base.path : '${base.path}/';
    if (!target.path.startsWith(prefix)) return null;
    if (target.hasAuthority && target.host != base.host) return null;
    final relative = target.path.substring(prefix.length - 1);
    return target.hasQuery ? '$relative?${target.query}' : relative;
  }

  /// Descarga un archivo protegido del API con la sesión. Devuelve `null`
  /// si la URL no pertenece al API, no existe o falla la red.
  Future<Uint8List?> getBytes(String url) async {
    final path = apiPathFor(url);
    if (path == null) return null;
    try {
      final response = await _dio.get<List<int>>(
        path,
        options: Options(responseType: ResponseType.bytes),
      );
      final data = response.data;
      return data == null || data.isEmpty ? null : Uint8List.fromList(data);
    } on DioException {
      return null;
    }
  }

  /// Sube un archivo en memoria como `multipart/form-data` con `PUT`, que es
  /// como el API sustituye un recurso (la foto propia).
  Future<Map<String, dynamic>> putFile(
    String path, {
    required String field,
    required Uint8List bytes,
    required String filename,
  }) {
    final form = FormData.fromMap({
      field: MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: _imageTypeOf(filename),
      ),
    });
    return putObject(path, data: form);
  }

  static DioMediaType? _imageTypeOf(String filename) {
    final extension = filename.split('.').last.toLowerCase();
    return switch (extension) {
      'jpg' || 'jpeg' => DioMediaType('image', 'jpeg'),
      'png' => DioMediaType('image', 'png'),
      'webp' => DioMediaType('image', 'webp'),
      _ => null,
    };
  }
}
