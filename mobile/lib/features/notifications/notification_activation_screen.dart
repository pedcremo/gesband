import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/ui/components.dart';
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
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: ScreenBar(
        title: strings.activateNotifications,
        actions: const [LanguageMenu()],
      ),
      body: SafeArea(
        top: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(GesbandSpacing.xl,
                    GesbandSpacing.sm, GesbandSpacing.xl, GesbandSpacing.xl),
                children: [
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: Container(
                      width: 72,
                      height: 72,
                      decoration: BoxDecoration(
                        color: t.primary,
                        borderRadius: BorderRadius.circular(t.radiusLarge),
                        border: t.primaryEdge == null
                            ? null
                            : Border.fromBorderSide(t.primaryEdgeSide),
                      ),
                      child: Icon(Icons.notifications_active_outlined,
                          size: 36, color: t.onPrimary),
                    ),
                  ),
                  const SizedBox(height: GesbandSpacing.lg),
                  Text(
                    strings.notificationExplanation,
                    style: text.titleMedium!.copyWith(fontSize: 18),
                  ),
                  const SizedBox(height: GesbandSpacing.xl),
                  if (!state.available)
                    InlineNotice(
                      icon: Icons.info_outline_rounded,
                      tone: Tone.neutral,
                      message: strings.notificationsUnavailable,
                    )
                  else ...[
                    SurfaceCard(
                      padding: const EdgeInsets.symmetric(
                          horizontal: GesbandSpacing.lg,
                          vertical: GesbandSpacing.sm),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _StatusRow(
                            key: const Key('permission-row'),
                            label: strings.permission,
                            value:
                                strings.permissionName(state.permission.name),
                            ok: state.permission == PushPermission.granted,
                          ),
                          _StatusRow(
                            key: const Key('registration-row'),
                            label: strings.registeredDevice,
                            value: state.tokenRegistered
                                ? strings.yes
                                : strings.no,
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
                              padding: const EdgeInsets.only(
                                  left: 40, bottom: GesbandSpacing.sm),
                              child: Text(
                                strings.lastReceiptAt(
                                  '${materialStrings.formatMediumDate(lastReceipt)} '
                                  '${materialStrings.formatTimeOfDay(TimeOfDay.fromDateTime(lastReceipt))}',
                                ),
                                style: text.bodySmall,
                              ),
                            ),
                          if (lastTest != null)
                            Padding(
                              padding: const EdgeInsets.only(
                                  left: 40, bottom: GesbandSpacing.sm),
                              child: Text(
                                '${strings.lastTest}: '
                                '${strings.testStatusName(lastTest.status.wireValue)}',
                                style: text.bodySmall,
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: GesbandSpacing.md),
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
                    const SizedBox(height: GesbandSpacing.md),
                    InlineNotice(
                      icon: Icons.error_outline_rounded,
                      tone: Tone.danger,
                      message: strings.message(state.error!),
                    ),
                  ],
                  if (state.loading) ...[
                    const SizedBox(height: GesbandSpacing.lg),
                    const LoadingView(),
                  ],
                ],
              ),
            ),
            // Las acciones quedan fijas abajo para que «Ahora no» siempre se
            // vea: el paso nunca bloquea el acceso a la app.
            DecoratedBox(
              decoration: BoxDecoration(
                color: t.background,
                border: Border(top: BorderSide(color: t.line)),
              ),
              // Con texto grande en pantallas bajas, las acciones se
              // desplazan en lugar de desbordar.
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.sizeOf(context).height * 0.5,
                ),
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(GesbandSpacing.xl,
                      GesbandSpacing.md, GesbandSpacing.xl, GesbandSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ..._actions(strings, state, action),
                      const SizedBox(height: GesbandSpacing.xs),
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
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: GesbandSpacing.sm),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: ok ? t.success : t.surfaceMuted,
              shape: BoxShape.circle,
            ),
            child: Icon(
              ok ? Icons.check_rounded : Icons.more_horiz_rounded,
              size: 18,
              color: ok ? t.successInk : t.muted,
            ),
          ),
          const SizedBox(width: GesbandSpacing.md),
          Expanded(
            child: Text('$label: $value',
                style: Theme.of(context).textTheme.bodyLarge),
          ),
        ],
      ),
    );
  }
}

class _Explanation extends StatelessWidget {
  const _Explanation(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: GesbandSpacing.sm),
        child: Text(text, style: Theme.of(context).textTheme.bodyLarge),
      );
}
