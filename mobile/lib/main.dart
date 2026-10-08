import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/api/api_client.dart';
import 'core/app_controller.dart';
import 'core/config/app_config.dart';
import 'core/localization/app_strings.dart';
import 'core/repositories/repositories.dart';
import 'core/storage/secure_session_store.dart';
import 'core/theme/theme_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/associations/association_picker_screen.dart';
import 'features/home/home_shell.dart';
import 'features/notifications/notification_activation_screen.dart';
import 'features/notifications/notification_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final preferences = await SharedPreferences.getInstance();
  final localeController = LocaleController(preferences);
  final store = SecureSessionStore();
  final config = AppConfig.fromEnvironment();
  final api = ApiClient(baseUrl: config.apiBaseUrl, sessionStore: store);
  api.selectLanguage(localeController.locale.languageCode);
  final notifications = NotificationController(
    gateway: FirebasePushGateway(),
    registrations: ApiDeviceRegistrationRepository(api),
    deviceStore: SharedPreferencesDeviceStateStore(),
    pendingTests: PendingPushTestStore.shared(),
    appVersion: config.appVersion,
    languageCode: localeController.locale.languageCode,
  );
  localeController.addListener(() {
    final language = localeController.locale.languageCode;
    api.selectLanguage(language);
    unawaited(notifications.setLanguage(language));
  });
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
  registerFontLicenses();
  final theme = ThemeController(preferences, loadImage: api.getBytes);
  runApp(GesbandApp(
    controller: controller,
    localeController: localeController,
    themeController: theme,
  ));
  await controller.initialize();
}

/// Licencias OFL de las fuentes empaquetadas, visibles en «Licencias».
void registerFontLicenses() {
  const families = {
    'Big Shoulders Display': 'BigShouldersDisplay',
    'Instrument Sans': 'InstrumentSans',
    'Libre Caslon Text': 'LibreCaslonText',
    'Public Sans': 'PublicSans',
    'Bricolage Grotesque': 'BricolageGrotesque',
    'Figtree': 'Figtree',
  };
  LicenseRegistry.addLicense(() async* {
    for (final MapEntry(key: name, value: file) in families.entries) {
      yield LicenseEntryWithLineBreaks(
        [name],
        await rootBundle.loadString('assets/fonts/licenses/$file-OFL.txt'),
      );
    }
  });
}

class GesbandApp extends StatefulWidget {
  const GesbandApp({
    super.key,
    required this.controller,
    required this.localeController,
    required this.themeController,
  });
  final AppController controller;
  final LocaleController localeController;
  final ThemeController themeController;

  @override
  State<GesbandApp> createState() => _GesbandAppState();
}

class _GesbandAppState extends State<GesbandApp> {
  String? _brandedAssociationId;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_followAssociation);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_followAssociation);
    super.dispose();
  }

  /// La marca cambia al elegir o cambiar de banda. Mientras no hay banda
  /// activa se conserva la última, que es la que se ve en el acceso.
  void _followAssociation() {
    final controller = widget.controller;
    if (controller.stage == AppStage.signedOut) {
      _brandedAssociationId = null;
      widget.themeController.clearSessionCache();
      return;
    }
    final association = controller.activeAssociation;
    if (association == null || association.id == _brandedAssociationId) {
      return;
    }
    _brandedAssociationId = association.id;
    widget.themeController.applyAssociation(association);
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    final localeController = widget.localeController;
    final themeController = widget.themeController;
    return ListenableBuilder(
      listenable:
          Listenable.merge([controller, localeController, themeController]),
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
        theme: themeController.light,
        darkTheme: themeController.dark,
        themeMode: themeController.themeMode,
        builder: (context, child) => LocaleScope(
          controller: localeController,
          child: ThemeScope(controller: themeController, child: child!),
        ),
        home: switch (controller.stage) {
          AppStage.loading => const BrandLoadingScreen(),
          AppStage.signedOut => LoginScreen(controller: controller),
          AppStage.selectAssociation =>
            AssociationPickerScreen(controller: controller),
          AppStage.notifications => NotificationActivationScreen(
              notifications: controller.notifications,
              onContinue: controller.finishNotificationStep,
            ),
          AppStage.ready => HomeShell(controller: controller),
        },
      ),
    );
  }
}
