import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import 'notification_service.dart';

/// Paso guiado de MUST-NOTIF-01. Muestra por separado permiso, registro y
/// recepción, y ofrece solo la acción que corresponde al estado actual.
/// No bloquea la app: siempre se puede continuar y el paso pendiente sigue
/// visible en la agenda.
class NotificationActivationScreen extends StatelessWidget {
  const NotificationActivationScreen({
    super.key,
    required this.notifications,
    required this.onContinue,
  });

  final NotificationController notifications;
  final VoidCallback onContinue;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: notifications,
        builder: (context, _) => _buildContent(context),
      );

  Widget _buildContent(BuildContext context) {
    final strings = AppStrings.of(context);
    final state = notifications.state;
    final action = state.nextAction;
    final materialStrings = MaterialLocalizations.of(context);
    final lastReceipt = state.lastReceiptConfirmedAt?.toLocal();
    final lastTest = state.lastTest;
    return Scaffold(
      appBar: AppBar(
        title: Text(strings.activateNotifications),
        actions: const [LanguageMenu()],
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(24),
                children: [
                  const Icon(Icons.notifications_active_outlined, size: 72),
                  const SizedBox(height: 16),
                  Text(
                    strings.notificationExplanation,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 24),
                  if (!state.available)
                    _Explanation(strings.notificationsUnavailable)
                  else ...[
                    _StatusRow(
                      key: const Key('permission-row'),
                      label: strings.permission,
                      value: strings.permissionName(state.permission.name),
                      ok: state.permission == PushPermission.granted,
                    ),
                    _StatusRow(
                      key: const Key('registration-row'),
                      label: strings.registeredDevice,
                      value: state.tokenRegistered ? strings.yes : strings.no,
                      ok: state.tokenRegistered,
                    ),
                    _StatusRow(
                      key: const Key('receipt-row'),
                      label: strings.receiptConfirmed,
                      value: state.receiptConfirmed
                          ? strings.yes
                          : strings.pending,
                      ok: state.receiptConfirmed,
                    ),
                    if (lastReceipt != null)
                      Padding(
                        padding: const EdgeInsets.only(left: 40, bottom: 8),
                        child: Text(strings.lastReceiptAt(
                          '${materialStrings.formatMediumDate(lastReceipt)} '
                          '${materialStrings.formatTimeOfDay(TimeOfDay.fromDateTime(lastReceipt))}',
                        )),
                      ),
                    if (lastTest != null)
                      Padding(
                        padding: const EdgeInsets.only(left: 40, bottom: 8),
                        child: Text(
                          '${strings.lastTest}: '
                          '${strings.testStatusName(lastTest.status.wireValue)}',
                        ),
                      ),
                    const SizedBox(height: 8),
                    if (state.permission == PushPermission.provisional)
                      _Explanation(strings.notificationsProvisionalExplanation),
                    if (action != NotificationAction.requestSystemPermission)
                      _Explanation(switch (action) {
                        NotificationAction.requestSystemPermission ||
                        NotificationAction.openSystemSettings =>
                          strings.notificationsDeniedExplanation,
                        NotificationAction.registerToken =>
                          strings.notificationsRegisterExplanation,
                        NotificationAction.runReceiveTest =>
                          strings.notificationsTestExplanation,
                        NotificationAction.none => strings.notificationsAllSet,
                      }),
                  ],
                  if (state.error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      strings.message(state.error!),
                      style:
                          TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ],
                  if (state.loading) ...[
                    const SizedBox(height: 16),
                    const Center(child: CircularProgressIndicator()),
                  ],
                ],
              ),
            ),
            // Las acciones quedan fijas abajo para que «Ahora no» siempre se
            // vea: el paso nunca bloquea el acceso a la app.
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  ..._actions(strings, state, action),
                  const SizedBox(height: 8),
                  TextButton(
                    key: const Key('continue-button'),
                    onPressed: onContinue,
                    child: Text(
                      state.fullyActive || !state.available
                          ? strings.continueLabel
                          : strings.notNow,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _actions(
    AppStrings strings,
    NotificationActivationState state,
    NotificationAction action,
  ) {
    if (!state.available) return const [];
    final busy = state.loading;
    return switch (action) {
      NotificationAction.requestSystemPermission => [
          FilledButton(
            key: const Key('request-permission-button'),
            onPressed: busy ? null : notifications.requestPermission,
            child: Text(strings.activateNotificationsButton),
          ),
        ],
      NotificationAction.openSystemSettings => [
          FilledButton(
            key: const Key('open-settings-button'),
            onPressed: notifications.openSettings,
            child: Text(strings.openSystemSettings),
          ),
        ],
      NotificationAction.registerToken => [
          FilledButton(
            key: const Key('register-button'),
            onPressed: busy ? null : notifications.refresh,
            child: Text(strings.registerDevice),
          ),
        ],
      NotificationAction.runReceiveTest || NotificationAction.none => [
          if (state.permission == PushPermission.provisional)
            OutlinedButton(
              onPressed: notifications.openSettings,
              child: Text(strings.openSystemSettings),
            ),
          FilledButton(
            key: const Key('foreground-test-button'),
            onPressed: busy
                ? null
                : () => notifications.sendTest(PushPresentation.foreground),
            child: Text(strings.sendTestNotification),
          ),
          const SizedBox(height: 8),
          OutlinedButton(
            key: const Key('background-test-button'),
            onPressed: busy
                ? null
                : () => notifications.sendTest(PushPresentation.background),
            child: Text(strings.sendBackgroundTest),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(strings.backgroundTestHint),
          ),
          if (state.lastTest != null)
            TextButton(
              onPressed: busy ? null : notifications.refreshTest,
              child: Text(strings.checkTestStatus),
            ),
        ],
    };
  }
}

class _StatusRow extends StatelessWidget {
  const _StatusRow({
    super.key,
    required this.label,
    required this.value,
    required this.ok,
  });

  final String label;
  final String value;
  final bool ok;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            Icon(
              ok ? Icons.check_circle : Icons.radio_button_unchecked,
              color: ok
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(width: 16),
            Expanded(child: Text('$label: $value')),
          ],
        ),
      );
}

class _Explanation extends StatelessWidget {
  const _Explanation(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(text),
      );
}
