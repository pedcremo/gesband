import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';
import 'absence_reason_dialog.dart';
import 'agenda_widgets.dart';

class ActivityDetailScreen extends StatefulWidget {
  const ActivityDetailScreen(
      {super.key,
      required this.association,
      required this.activityId,
      required this.repository});
  final Association association;
  final String activityId;
  final ActivitiesRepository repository;
  @override
  State<ActivityDetailScreen> createState() => _ActivityDetailScreenState();
}

class _ActivityDetailScreenState extends State<ActivityDetailScreen> {
  late Future<ActivityDetail> future;
  bool sending = false;

  @override
  void initState() {
    super.initState();
    future =
        widget.repository.getById(widget.association.id, widget.activityId);
  }

  Future<void> send(InvitationResponse value, {String note = ''}) async {
    setState(() => sending = true);
    try {
      final result = await widget.repository
          .respond(widget.association.id, widget.activityId, value, note: note);
      if (!mounted) return;
      setState(() {
        future = Future.value(result);
      });
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppStrings.of(context).responseSaved)));
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppStrings.of(context).responseFailed)));
    } finally {
      if (mounted) setState(() => sending = false);
    }
  }

  Future<void> declineMandatory() async {
    final reason = await askAbsenceReason(context);
    if (reason != null && mounted) {
      await send(InvitationResponse.declined, note: reason);
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      appBar: ScreenBar(
        title: strings.activity,
        actions: const [LanguageMenu()],
      ),
      body: FutureBuilder<ActivityDetail>(
        future: future,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return MessageView(
              icon: Icons.cloud_off_rounded,
              tone: Tone.danger,
              message: strings.genericError,
              actionLabel: strings.retry,
              onAction: () => setState(() {
                future = widget.repository
                    .getById(widget.association.id, widget.activityId);
              }),
            );
          }
          if (!snapshot.hasData) return const LoadingView();
          final activity = snapshot.data!;
          return _ActivityDetailBody(
            activity: activity,
            sending: sending,
            onAccept: () => send(InvitationResponse.accepted),
            onDecline: activity.summary.isMandatory
                ? declineMandatory
                : () => send(InvitationResponse.declined),
          );
        },
      ),
    );
  }
}

class _ActivityDetailBody extends StatelessWidget {
  const _ActivityDetailBody({
    required this.activity,
    required this.sending,
    required this.onAccept,
    required this.onDecline,
  });

  final ActivityDetail activity;
  final bool sending;
  final VoidCallback onAccept;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    final summary = activity.summary;
    final response = summary.invitationResponse;
    final transport = activity.transport;
    final paid = paidLabel(context, summary);

    final notice = switch (summary.status) {
      ActivityStatus.cancelled => strings.activityCancelledNotice,
      _ when activity.invitationId == null => strings.notInvitedNotice,
      _ when DateTime.now().isAfter(summary.startsAt) =>
        strings.activityPastNotice,
      _ when activity.deadlinePassed => strings.deadlinePassedNotice,
      _ when summary.needsReconfirmation => strings.reconfirmNotice,
      _ => null,
    };

    final facts = <(IconData, String, String)>[
      (
        Icons.event_rounded,
        strings.startsLabel,
        dates.dateTime(summary.startsAt)
      ),
      if (activity.endsAt != null)
        (
          Icons.event_available_rounded,
          strings.endsLabel,
          dates.dateTime(activity.endsAt!)
        ),
      if (activity.meetingAt != null)
        (
          Icons.groups_rounded,
          strings.meetingLabel,
          dates.dateTime(activity.meetingAt!)
        ),
      if (summary.place?.isNotEmpty ?? false)
        (Icons.place_outlined, strings.placeLabel, summary.place!),
      if (activity.uniform != null)
        (Icons.checkroom_rounded, strings.uniform, activity.uniform!),
      if (activity.responseDeadline != null)
        (
          Icons.schedule_rounded,
          strings.deadlineLabel,
          dates.dateTime(activity.responseDeadline!)
        ),
    ];

    return ListView(
      padding: const EdgeInsets.fromLTRB(
          GesbandSpacing.xl, GesbandSpacing.sm, GesbandSpacing.xl, 40),
      children: [
        Wrap(
          spacing: GesbandSpacing.sm,
          runSpacing: GesbandSpacing.sm,
          children: [
            StatusPill(
                label: strings.activityTypeName(summary.type),
                tone: Tone.brand),
            if (summary.isMandatory)
              StatusPill(label: strings.mandatoryShort, tone: Tone.warning),
            if (paid != null)
              StatusPill(
                  key: const Key('paid-indicator'),
                  label: paid,
                  tone: Tone.success),
          ],
        ),
        const SizedBox(height: GesbandSpacing.md),
        Semantics(header: true, child: DisplayText(summary.title, size: 36)),
        if (notice != null) ...[
          const SizedBox(height: GesbandSpacing.lg),
          InlineNotice(
            icon: Icons.info_outline_rounded,
            message: notice,
            tone: summary.status == ActivityStatus.cancelled
                ? Tone.danger
                : Tone.warning,
          ),
        ],
        const SizedBox(height: GesbandSpacing.lg),
        SurfaceCard(
          padding: const EdgeInsets.symmetric(
              horizontal: GesbandSpacing.lg, vertical: GesbandSpacing.sm),
          child: Column(
            children: [
              for (final (icon, label, value) in facts)
                _FactRow(icon: icon, label: label, value: value),
            ],
          ),
        ),
        if (transport != null) ...[
          const SizedBox(height: GesbandSpacing.lg),
          SurfaceCard(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _IconTile(icon: Icons.directions_bus_rounded),
                const SizedBox(width: GesbandSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(strings.transport, style: text.bodySmall),
                      Text(transport.label, style: text.titleMedium),
                      for (final line in [
                        if (transport.meetingPoint != null)
                          '${strings.meetingPointLabel}: ${transport.meetingPoint}',
                        if (transport.departureAt != null)
                          '${strings.departureLabel}: ${dates.dateTime(transport.departureAt!)}',
                        if (transport.driverName != null)
                          '${strings.driverLabel}: ${transport.driverName}',
                      ])
                        Text(line, style: text.bodyMedium),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
        if (summary.isMandatory) ...[
          const SizedBox(height: GesbandSpacing.lg),
          InlineNotice(
            icon: Icons.priority_high_rounded,
            tone: Tone.neutral,
            message:
                '${strings.mandatoryActivity}. ${strings.mandatoryActivityExplanation}',
          ),
        ],
        if (activity.description != null) ...[
          const SizedBox(height: GesbandSpacing.lg),
          Text(activity.description!, style: text.bodyLarge),
        ],
        if (activity.programme.isNotEmpty) ...[
          const SizedBox(height: GesbandSpacing.xxl),
          SectionTitle(strings.programme),
          const SizedBox(height: GesbandSpacing.sm),
          SurfaceCard(
            padding: const EdgeInsets.symmetric(
                horizontal: GesbandSpacing.lg, vertical: GesbandSpacing.xs),
            child: Column(
              children: [
                for (var i = 0; i < activity.programme.length; i++)
                  _ProgrammeRow(
                    position: i + 1,
                    item: activity.programme[i],
                    divided: i > 0,
                  ),
              ],
            ),
          ),
        ],
        if (activity.invitationId != null) ...[
          const SizedBox(height: GesbandSpacing.xxl),
          SectionTitle(strings.yourResponse),
          const SizedBox(height: GesbandSpacing.sm),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: StatusPill(
              key: const Key('current-response'),
              label: strings.responseName(response),
              tone: switch (response) {
                InvitationResponse.accepted => Tone.success,
                InvitationResponse.declined => Tone.danger,
                InvitationResponse.pending => Tone.warning,
              },
            ),
          ),
          if (activity.responseNote != null)
            Padding(
              padding: const EdgeInsets.only(top: GesbandSpacing.sm),
              child: Text(
                '${strings.absenceReason}: ${activity.responseNote}',
                style: text.bodyMedium!.copyWith(color: t.muted),
              ),
            ),
          if (activity.canRespond) ...[
            const SizedBox(height: GesbandSpacing.md),
            _ResponseChoice(
              key: const Key('response-buttons'),
              response: response,
              enabled: !sending,
              onAccept: onAccept,
              onDecline: onDecline,
            ),
            if (sending)
              const Padding(
                padding: EdgeInsets.only(top: GesbandSpacing.md),
                child: LinearProgressIndicator(),
              ),
          ],
        ],
      ],
    );
  }
}

class _IconTile extends StatelessWidget {
  const _IconTile({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: t.primaryTint,
        borderRadius: BorderRadius.circular(t.radiusSmall),
      ),
      child: Icon(icon, size: 22, color: t.onPrimaryTint),
    );
  }
}

class _FactRow extends StatelessWidget {
  const _FactRow(
      {required this.icon, required this.label, required this.value});

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return MergeSemantics(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: GesbandSpacing.sm),
        child: Row(
          children: [
            _IconTile(icon: icon),
            const SizedBox(width: GesbandSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: text.bodySmall),
                  Text(value, style: text.titleMedium),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProgrammeRow extends StatelessWidget {
  const _ProgrammeRow({
    required this.position,
    required this.item,
    required this.divided,
  });

  final int position;
  final ProgrammeItem item;
  final bool divided;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    return Container(
      decoration: BoxDecoration(
        border: divided ? Border(top: BorderSide(color: t.line)) : null,
      ),
      padding: const EdgeInsets.symmetric(vertical: GesbandSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 32,
            child:
                Text('$position', style: t.display(20, color: t.primaryText)),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.title, style: text.titleMedium),
                if (item.notes != null && item.notes!.isNotEmpty)
                  Text(item.notes!, style: text.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Dos botones grandes: el elegido va relleno. Pulsar el ya elegido no hace
/// nada, igual que el selector anterior.
class _ResponseChoice extends StatelessWidget {
  const _ResponseChoice({
    super.key,
    required this.response,
    required this.enabled,
    required this.onAccept,
    required this.onDecline,
  });

  final InvitationResponse response;
  final bool enabled;
  final VoidCallback onAccept;
  final VoidCallback onDecline;

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    Widget option(InvitationResponse value, IconData icon, String label,
        VoidCallback onTap) {
      final chosen = response == value;
      final onPressed = !enabled ? null : (chosen ? () {} : onTap);
      final child = Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(chosen ? Icons.check_rounded : icon, size: 20),
          const SizedBox(width: 6),
          Flexible(child: Text(label, textAlign: TextAlign.center)),
        ],
      );
      return Semantics(
        selected: chosen,
        child: chosen
            ? FilledButton(onPressed: onPressed, child: child)
            : OutlinedButton(onPressed: onPressed, child: child),
      );
    }

    return Row(
      children: [
        Expanded(
          child: option(InvitationResponse.accepted, Icons.check_rounded,
              strings.accept, onAccept),
        ),
        const SizedBox(width: GesbandSpacing.sm),
        Expanded(
          child: option(InvitationResponse.declined, Icons.close_rounded,
              strings.decline, onDecline),
        ),
      ],
    );
  }
}
