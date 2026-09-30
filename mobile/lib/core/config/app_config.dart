class AppConfig {
  const AppConfig({required this.apiBaseUrl, required this.appVersion});

  factory AppConfig.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    final uri = Uri.tryParse(baseUrl);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
      throw StateError('API_BASE_URL debe ser una URL absoluta');
    }
    return const AppConfig(apiBaseUrl: baseUrl, appVersion: appVersionName);
  }

  /// Versión que se comunica al registrar el dispositivo. Mantener igual que
  /// `version` de pubspec.yaml o fijarla con `--dart-define=APP_VERSION=...`.
  static const appVersionName =
      String.fromEnvironment('APP_VERSION', defaultValue: '0.1.0+1');

  final String apiBaseUrl;
  final String appVersion;
}
