class AppConfig {
  const AppConfig({required this.apiBaseUrl});

  factory AppConfig.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    final uri = Uri.tryParse(baseUrl);
    if (uri == null || !uri.hasScheme || !uri.hasAuthority) {
      throw StateError('API_BASE_URL debe ser una URL absoluta');
    }
    return const AppConfig(apiBaseUrl: baseUrl);
  }

  final String apiBaseUrl;
}
