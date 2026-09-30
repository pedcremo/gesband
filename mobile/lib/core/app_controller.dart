import 'dart:async';

import 'package:flutter/material.dart';

import '../features/activities/activity_detail_screen.dart';
import '../features/polls/poll_detail_screen.dart';
import '../features/notifications/notification_service.dart';
import 'api/api_client.dart';
import 'localization/app_strings.dart';
import 'models/models.dart';
import 'repositories/repositories.dart';

enum AppStage { loading, signedOut, selectAssociation, notifications, ready }

class AppController extends ChangeNotifier {
  AppController({
    required this.api,
    required this.auth,
    required this.associationsRepository,
    required this.activitiesRepository,
    required this.profileRepository,
    required this.inboxRepository,
    required this.pollsRepository,
    required this.agendaCache,
    required this.notifications,
  });

  final ApiClient api;
  final AuthRepository auth;
  final AssociationsRepository associationsRepository;
  final ActivitiesRepository activitiesRepository;
  final ProfileRepository profileRepository;
  final InboxRepository inboxRepository;
  final PollsRepository pollsRepository;
  final AgendaCache agendaCache;
  final NotificationController notifications;
  final navigatorKey = GlobalKey<NavigatorState>();
  final scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

  AppStage _stage = AppStage.loading;
  List<Association> _associations = const [];
  Association? _activeAssociation;
  AppMessage? _error;
  NotificationTarget? _pendingTarget;
  StreamSubscription<NotificationTarget>? _linkSubscription;
  StreamSubscription<PushEnvelope>? _messageSubscription;
  StreamSubscription<void>? _deactivationSubscription;

  /// Aumenta al llegar un aviso en primer plano para que la agenda se
  /// actualice sin que la persona tenga que tirar de la lista.
  final contentRevision = ValueNotifier<int>(0);

  AppStage get stage => _stage;
  List<Association> get associations => _associations;
  Association? get activeAssociation => _activeAssociation;
  AppMessage? get error => _error;

  Future<void> initialize() async {
    _linkSubscription = notifications.targets.listen(openTarget);
    _messageSubscription =
        notifications.foregroundMessages.listen(_showForegroundMessage);
    _deactivationSubscription =
        notifications.deactivations.listen((_) => _showDeactivation());
    await notifications.initialize();
    if (await auth.hasSession()) {
      unawaited(notifications.bindSession());
      await _loadAssociations();
    } else {
      _setStage(AppStage.signedOut);
    }
  }

  Future<void> login(String email, String password) async {
    _error = null;
    _setStage(AppStage.loading);
    try {
      await auth.login(email: email, password: password);
      unawaited(notifications.bindSession());
      await _loadAssociations();
    } catch (_) {
      _error = AppMessage.signInFailed;
      _setStage(AppStage.signedOut);
    }
  }

  Future<void> _loadAssociations() async {
    try {
      _associations = await associationsRepository.listMine();
      if (_associations.length == 1) {
        selectAssociation(_associations.single);
      } else {
        _setStage(AppStage.selectAssociation);
      }
    } catch (_) {
      _error = AppMessage.associationsLoadFailed;
      _setStage(AppStage.signedOut);
    }
  }

  void selectAssociation(Association association) {
    _activeAssociation = association;
    api.selectAssociation(association.id);
    _setStage(AppStage.notifications);
  }

  void finishNotificationStep() {
    _setStage(AppStage.ready);
    final pending = _pendingTarget;
    _pendingTarget = null;
    if (pending != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => openTarget(pending));
    }
  }

  void changeAssociation() {
    _activeAssociation = null;
    api.selectAssociation(null);
    _setStage(AppStage.selectAssociation);
  }

  Future<void> logout() async {
    _setStage(AppStage.loading);
    _pendingTarget = null;
    scaffoldMessengerKey.currentState?.clearSnackBars();
    await notifications.unbindSession();
    await agendaCache.clearAll();
    await auth.logout();
    api.selectAssociation(null);
    _activeAssociation = null;
    _associations = const [];
    _setStage(AppStage.signedOut);
  }

  /// Abre la actividad o encuesta de un aviso. Si todavía no hay sesión y
  /// banda elegida, lo guarda para abrirlo al terminar la incorporación.
  void openTarget(NotificationTarget target) {
    final association = _activeAssociation;
    final navigator = navigatorKey.currentState;
    if (_stage != AppStage.ready || association == null || navigator == null) {
      _pendingTarget = target;
      return;
    }
    navigator.push(
      MaterialPageRoute<void>(
        builder: (_) => switch (target) {
          ActivityTarget(:final id) => ActivityDetailScreen(
              association: association,
              activityId: id,
              repository: activitiesRepository,
            ),
          PollTarget(:final id) => PollDetailScreen(
              association: association,
              pollId: id,
              repository: pollsRepository,
            ),
        },
      ),
    );
  }

  void _showForegroundMessage(PushEnvelope envelope) {
    if (_stage == AppStage.signedOut) return;
    contentRevision.value++;
    final messenger = scaffoldMessengerKey.currentState;
    final strings = _strings;
    if (messenger == null || strings == null) return;
    final target = envelope.target;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            envelope.isTest
                ? strings.testNotificationReceived
                : envelope.title ?? envelope.body ?? strings.newNotification,
          ),
          action: target == null
              ? null
              : SnackBarAction(
                  label: strings.open,
                  onPressed: () => openTarget(target),
                ),
        ),
      );
  }

  void _showDeactivation() {
    if (_stage == AppStage.signedOut) return;
    final messenger = scaffoldMessengerKey.currentState;
    final strings = _strings;
    if (messenger == null || strings == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          duration: const Duration(seconds: 10),
          content: Text(strings.notificationsDisabledDetected),
          action: SnackBarAction(
            label: strings.openSystemSettings,
            onPressed: notifications.openSettings,
          ),
        ),
      );
  }

  /// El ScaffoldMessenger de MaterialApp está por encima de Localizations:
  /// los textos se leen desde el contexto del Navigator.
  AppStrings? get _strings {
    final context = navigatorKey.currentContext;
    return context == null
        ? null
        : Localizations.of<AppStrings>(context, AppStrings);
  }

  void _setStage(AppStage value) {
    _stage = value;
    notifyListeners();
  }

  @override
  void dispose() {
    unawaited(_linkSubscription?.cancel());
    unawaited(_messageSubscription?.cancel());
    unawaited(_deactivationSubscription?.cancel());
    contentRevision.dispose();
    notifications.dispose();
    super.dispose();
  }
}
