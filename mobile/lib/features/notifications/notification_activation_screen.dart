import 'package:flutter/material.dart';
import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import 'notification_service.dart';

class NotificationActivationScreen extends StatelessWidget {
  const NotificationActivationScreen({super.key, required this.controller});
  final AppController controller;
  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller.notifications,
      builder: (context, _) => _buildContent(context),
    );
  }

  Widget _buildContent(BuildContext context) {
    final strings = AppStrings.of(context);
    final state = controller.notifications.state;
    final enabled = state.permission == PushPermission.authorized ||
        state.permission == PushPermission.provisional;
    return Scaffold(
        appBar: AppBar(
          title: Text(strings.activateNotifications),
          actions: const [LanguageMenu()],
        ),
        body: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.notifications_active_outlined, size: 72),
                  const SizedBox(height: 16),
                  Text(strings.notificationExplanation,
                      style: TextStyle(fontSize: 18)),
                  const SizedBox(height: 24),
                  Text('${strings.permission}: '
                      '${strings.permissionName(state.permission.name)}'),
                  Text('${strings.registeredDevice}: '
                      '${state.tokenRegistered ? strings.yes : strings.no}'),
                  Text('${strings.testReceived}: '
                      '${state.testReceiptConfirmed ? strings.yes : strings.pending}'),
                  if (state.error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      strings.message(state.error!),
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const Spacer(),
                  if (!enabled)
                    FilledButton(
                        onPressed: state.loading
                            ? null
                            : controller.notifications.requestPermission,
                        child: Text(strings.activateNotificationsButton)),
                  if (!enabled && (state.permission == PushPermission.denied))
                    OutlinedButton(
                        onPressed: controller.notifications.openSettings,
                        child: Text(strings.openSystemSettings)),
                  if (enabled && !state.testReceiptConfirmed)
                    OutlinedButton(
                        onPressed: state.loading
                            ? null
                            : controller.notifications.sendTest,
                        child: Text(strings.sendTestNotification)),
                  FilledButton(
                      onPressed: state.tokenRegistered
                          ? controller.finishNotificationStep
                          : null,
                      child: Text(strings.continueLabel)),
                ])));
  }
}
