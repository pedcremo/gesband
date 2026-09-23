import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SessionTokens {
  const SessionTokens({required this.accessToken, required this.refreshToken});

  final String accessToken;
  final String refreshToken;
}

abstract interface class SessionStore {
  Future<SessionTokens?> readTokens();
  Future<void> writeTokens(SessionTokens tokens);
  Future<void> clear();
}

class SecureSessionStore implements SessionStore {
  SecureSessionStore({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _accessKey = 'session_access_token';
  static const _refreshKey = 'session_refresh_token';
  final FlutterSecureStorage _storage;

  @override
  Future<SessionTokens?> readTokens() async {
    final access = await _storage.read(key: _accessKey);
    final refresh = await _storage.read(key: _refreshKey);
    if (access == null || refresh == null) return null;
    return SessionTokens(accessToken: access, refreshToken: refresh);
  }

  @override
  Future<void> writeTokens(SessionTokens tokens) async {
    await _storage.write(key: _accessKey, value: tokens.accessToken);
    await _storage.write(key: _refreshKey, value: tokens.refreshToken);
  }

  @override
  Future<void> clear() => _storage.deleteAll();
}
