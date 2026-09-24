import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/api/api_client.dart';
import 'core/app_controller.dart';
import 'core/config/app_config.dart';
import 'core/localization/app_strings.dart';
import 'core/repositories/repositories.dart';
import 'core/storage/secure_session_store.dart';
import 'features/auth/login_screen.dart';
import 'features/activities/agenda_screen.dart';
import 'features/associations/association_picker_screen.dart';
import 'features/notifications/notification_activation_screen.dart';
import 'features/notifications/notification_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final preferences = await SharedPreferences.getInstance();
  final localeController = LocaleController(preferences);
  final store = SecureSessionStore();
  final api = ApiClient(
      baseUrl: AppConfig.fromEnvironment().apiBaseUrl, sessionStore: store);
  api.selectLanguage(localeController.locale.languageCode);
  localeController.addListener(
    () => api.selectLanguage(localeController.locale.languageCode),
  );
  final notifications = NotificationController(
    gateway: FirebasePushGateway(),
    registrations: ApiDeviceRegistrationRepository(api),
  );
  final controller = AppController(
    api: api,
    auth: ApiAuthRepository(api, store),
    associationsRepository: ApiAssociationsRepository(api),
    activitiesRepository:
        ApiActivitiesRepository(api, AgendaCache(preferences)),
    profileRepository: ApiProfileRepository(api),
    inboxRepository: ApiInboxRepository(api),
    pollsRepository: ApiPollsRepository(api),
    agendaCache: AgendaCache(preferences),
    notifications: notifications,
  );
  runApp(GesbandApp(
    controller: controller,
    localeController: localeController,
  ));
  await controller.initialize();
}

class GesbandApp extends StatelessWidget {
  const GesbandApp({
    super.key,
    required this.controller,
    required this.localeController,
  });
  final AppController controller;
  final LocaleController localeController;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: Listenable.merge([controller, localeController]),
        builder: (context, _) => MaterialApp(
          navigatorKey: controller.navigatorKey,
          scaffoldMessengerKey: controller.scaffoldMessengerKey,
          title: 'Gesband',
          locale: localeController.locale,
          localizationsDelegates: const [
            AppStrings.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppStrings.supportedLocales,
          theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
          builder: (context, child) => LocaleScope(
            controller: localeController,
            child: child!,
          ),
          home: switch (controller.stage) {
            AppStage.loading =>
              const Scaffold(body: Center(child: CircularProgressIndicator())),
            AppStage.signedOut => LoginScreen(controller: controller),
            AppStage.selectAssociation =>
              AssociationPickerScreen(controller: controller),
            AppStage.notifications =>
              NotificationActivationScreen(controller: controller),
            AppStage.ready => AgendaScreen(controller: controller),
          },
        ),
      );
}
