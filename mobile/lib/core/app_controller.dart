import 'dart:async';

import 'package:flutter/material.dart';

import '../features/activities/activity_detail_screen.dart';
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
  String? _pendingActivityId;
  StreamSubscription<String>? _linkSubscription;
  StreamSubscription<PushEnvelope>? _messageSubscription;

  AppStage get stage => _stage;
  List<Association> get associations => _associations;
  Association? get activeAssociation => _activeAssociation;
  AppMessage? get error => _error;

  Future<void> initialize() async {
    _linkSubscription = notifications.activityLinks.listen(_openActivity);
    _messageSubscription =
        notifications.foregroundMessages.listen(_showForegroundMessage);
    await notifications.initialize();
    if (await auth.hasSession()) {
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
      await notifications.bindSession();
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
    final pending = _pendingActivityId;
    _pendingActivityId = null;
    if (pending != null) {
      WidgetsBinding.instance
          .addPostFrameCallback((_) => _openActivity(pending));
    }
  }

  void changeAssociation() {
    _activeAssociation = null;
    api.selectAssociation(null);
    _setStage(AppStage.selectAssociation);
  }

  Future<void> logout() async {
    _setStage(AppStage.loading);
    await notifications.unbindSession();
    await agendaCache.clearAll();
    await auth.logout();
    api.selectAssociation(null);
    _activeAssociation = null;
    _associations = const [];
    _setStage(AppStage.signedOut);
  }

  void _openActivity(String activityId) {
    final association = _activeAssociation;
    final context = navigatorKey.currentContext;
    if (_stage != AppStage.ready || association == null || context == null) {
      _pendingActivityId = activityId;
      return;
    }
    navigatorKey.currentState?.push(
      MaterialPageRoute<void>(
        builder: (_) => ActivityDetailScreen(
          association: association,
          activityId: activityId,
          repository: activitiesRepository,
        ),
      ),
    );
  }

  void _showForegroundMessage(PushEnvelope envelope) {
    final messenger = scaffoldMessengerKey.currentState;
    if (messenger == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            envelope.title ??
                envelope.body ??
                AppStrings.of(messenger.context).newNotification,
          ),
          action: envelope.activityId == null
              ? null
              : SnackBarAction(
                  label: AppStrings.of(messenger.context).open,
                  onPressed: () => _openActivity(envelope.activityId!),
                ),
        ),
      );
  }

  void _setStage(AppStage value) {
    _stage = value;
    notifyListeners();
  }

  @override
  void dispose() {
    unawaited(_linkSubscription?.cancel());
    unawaited(_messageSubscription?.cancel());
    notifications.dispose();
    super.dispose();
  }
}
