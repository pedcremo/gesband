import 'package:dio/dio.dart';

import '../storage/secure_session_store.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.statusCode, this.code});

  final String message;
  final int? statusCode;
  final String? code;

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
          handler.reject(
            DioException(
              requestOptions: error.requestOptions,
              response: error.response,
              error: ApiException(
                (body?['message'] as String?) ??
                    (body?['detail'] as String?) ??
                    'No se pudo completar la petición',
                statusCode: error.response?.statusCode,
                code: body?['code'] as String?,
              ),
            ),
          );
        },
      ),
    );
  }

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
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(path, data: data);
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
  }) async {
    try {
      final response = await _dio.patch<Map<String, dynamic>>(path, data: data);
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

  Future<Map<String, dynamic>> uploadFile(
    String path, {
    required String field,
    required String filePath,
  }) async {
    final form = FormData.fromMap({
      field: await MultipartFile.fromFile(filePath),
    });
    return postObject(path, data: form);
  }
}
