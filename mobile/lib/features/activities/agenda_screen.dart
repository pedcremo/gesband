import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/theme/visual_style.dart';
import '../../core/ui/brand_header.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';
import '../notifications/notification_activation_screen.dart';
import '../notifications/notification_service.dart';
import 'absence_reason_dialog.dart';
import 'activity_detail_screen.dart';
import 'agenda_widgets.dart';

/// Agenda: cartel de la próxima convocatoria y el resto agrupado por meses.
class AgendaScreen extends StatefulWidget {
  const AgendaScreen({super.key, required this.controller});
  final AppController controller;
  @override
  State<AgendaScreen> createState() => _AgendaScreenState();
}

class _AgendaScreenState extends State<AgendaScreen> {
  late Future<AgendaSnapshot> future;
  String? sendingId;

  @override
  void initState() {
    super.initState();
    future = widget.controller.activitiesRepository
        .listMine(widget.controller.activeAssociation!.id);
    widget.controller.contentRevision.addListener(_onContentChanged);
  }

  @override
  void dispose() {
    widget.controller.contentRevision.removeListener(_onContentChanged);
    super.dispose();
  }

  void _onContentChanged() {
    if (mounted) reload();
  }

  void _openNotificationStep() {
    Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (routeContext) => NotificationActivationScreen(
        notifications: widget.controller.notifications,
        onContinue: () => Navigator.of(routeContext).pop(),
      ),
    ));
  }

  Future<void> reload() async {
    setState(() {
      future = widget.controller.activitiesRepository
          .listMine(widget.controller.activeAssociation!.id);
    });
    await future;
  }

  Future<void> _open(ActivitySummary item) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => ActivityDetailScreen(
        association: widget.controller.activeAssociation!,
        activityId: item.id,
        repository: widget.controller.activitiesRepository,
      ),
    ));
    if (mounted) await reload();
  }

  /// Respuesta desde el cartel, con las mismas reglas que el detalle: una
  /// ausencia a una actividad obligatoria exige motivo.
  Future<void> _respond(ActivitySummary item, InvitationResponse value) async {
    var note = '';
    if (value == InvitationResponse.declined && item.isMandatory) {
      final reason = await askAbsenceReason(context);
      if (reason == null || !mounted) return;
      note = reason;
    }
    setState(() => sendingId = item.id);
    final messenger = ScaffoldMessenger.of(context);
    final strings = AppStrings.of(context);
    try {
      await widget.controller.activitiesRepository.respond(
          widget.controller.activeAssociation!.id, item.id, value,
          note: note);
      messenger.showSnackBar(SnackBar(content: Text(strings.responseSaved)));
      if (mounted) await reload();
    } catch (_) {
      messenger.showSnackBar(SnackBar(content: Text(strings.responseFailed)));
    } finally {
      if (mounted) setState(() => sendingId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final brand = ThemeScope.brandOf(context);
    return FutureBuilder<AgendaSnapshot>(
      future: future,
      builder: (context, snapshot) {
        final now = DateTime.now();
        final items = [...?snapshot.data?.activities]
          ..sort((a, b) => a.startsAt.compareTo(b.startsAt));
        final pending = items.where((item) => awaitsReply(item, now)).length;
        final t = GesbandTokens.of(context);
        final header = BrandHeader(
          brand: brand,
          // Festa saluda con el recuento de respuestas pendientes.
          title: t.style == VisualStyle.festa && snapshot.hasData
              ? strings.pendingReplies(pending)
              : null,
        );
        final children = <Widget>[
          header,
          _NotificationsBanner(
            notifications: widget.controller.notifications,
            onReview: _openNotificationStep,
          ),
        ];
        if (snapshot.hasError) {
          children.add(SizedBox(
            height: 360,
            child: MessageView(
              icon: Icons.cloud_off_rounded,
              tone: Tone.danger,
              message: strings.genericError,
              actionLabel: strings.retry,
              onAction: reload,
            ),
          ));
        } else if (!snapshot.hasData) {
          children.add(const SizedBox(height: 360, child: LoadingView()));
        } else {
          children.addAll(_content(context, snapshot.data!, items, now));
        }
        return RefreshIndicator(
          onRefresh: reload,
          child: ListView(
            padding: const EdgeInsets.only(bottom: GesbandSpacing.xxl),
            children: children,
          ),
        );
      },
    );
  }

  List<Widget> _content(BuildContext context, AgendaSnapshot agenda,
      List<ActivitySummary> items, DateTime now) {
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final t = GesbandTokens.of(context);
    final horizontal = t.style == VisualStyle.partitura
        ? GesbandSpacing.xxl
        : GesbandSpacing.xl;
    Widget padded(Widget child, {double top = GesbandSpacing.lg}) => Padding(
          padding: EdgeInsets.fromLTRB(horizontal, top, horizontal, 0),
          child: child,
        );

    final widgets = <Widget>[];
    if (agenda.cachedAt != null) {
      final cachedAt = agenda.cachedAt!;
      widgets.add(padded(
        InlineNotice(
          key: const Key('offline-agenda'),
          icon: Icons.cloud_off_rounded,
          message: strings.offlineAgenda(
            '${MaterialLocalizations.of(context).formatMediumDate(cachedAt)} · '
            '${dates.time(cachedAt)}',
          ),
          actionLabel: strings.retry,
          onAction: reload,
        ),
      ));
    }
    if (items.isEmpty) {
      widgets.add(SizedBox(
        height: 320,
        child: MessageView(
          icon: Icons.event_available_rounded,
          message: strings.emptyAgenda,
        ),
      ));
      return widgets;
    }

    final next = items
        .where((item) =>
            item.status == ActivityStatus.published &&
            item.startsAt.isAfter(now))
        .firstOrNull;
    if (next != null) {
      widgets.add(padded(
        ActivityPoster(
          item: next,
          canRespond: next.canRespondAt(now) && agenda.cachedAt == null,
          sending: sendingId == next.id,
          onOpen: () => _open(next),
          onRespond: (value) => _respond(next, value),
        ),
        top: GesbandSpacing.sm,
      ));
    }

    final rest = items.where((item) => item.id != next?.id).toList();
    String? month;
    for (final item in rest) {
      final title = dates.monthTitle(item.startsAt, now);
      if (title != month) {
        month = title;
        widgets.add(padded(SectionTitle(title), top: GesbandSpacing.xxl));
        widgets.add(const SizedBox(height: GesbandSpacing.sm));
      }
      widgets.add(padded(
        ActivityRow(
          item: item,
          highlighted: awaitsReply(item, now),
          onOpen: () => _open(item),
        ),
        top: t.style == VisualStyle.partitura ? 0 : 10,
      ));
    }
    return widgets;
  }
}

/// Recordatorio de MUST-NOTIF-01 mientras los avisos no estén completos.
class _NotificationsBanner extends StatelessWidget {
  const _NotificationsBanner({
    required this.notifications,
    required this.onReview,
  });

  final NotificationController notifications;
  final VoidCallback onReview;

  @override
  Widget build(BuildContext context) => ListenableBuilder(
        listenable: notifications,
        builder: (context, _) {
          final state = notifications.state;
          if (!state.available || state.nextAction == NotificationAction.none) {
            return const SizedBox.shrink();
          }
          final strings = AppStrings.of(context);
          return Padding(
            padding: const EdgeInsets.fromLTRB(
                GesbandSpacing.xl, GesbandSpacing.md, GesbandSpacing.xl, 0),
            child: InlineNotice(
              key: const Key('notifications-pending-banner'),
              icon: Icons.notifications_off_outlined,
              message: strings.notificationsPendingBanner,
              actionLabel: strings.review,
              onAction: onReview,
            ),
          );
        },
      );
}
