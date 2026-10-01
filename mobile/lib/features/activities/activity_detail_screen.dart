import 'package:flutter/material.dart';

import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';

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
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => const _AbsenceReasonDialog(),
    );
    if (reason != null && mounted) {
      await send(InvitationResponse.declined, note: reason);
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Text(strings.activity),
        actions: const [LanguageMenu()],
      ),
      body: FutureBuilder<ActivityDetail>(
        future: future,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(strings.genericError),
                  const SizedBox(height: 8),
                  OutlinedButton(
                    onPressed: () => setState(() {
                      future = widget.repository
                          .getById(widget.association.id, widget.activityId);
                    }),
                    child: Text(strings.retry),
                  ),
                ],
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
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
    final material = MaterialLocalizations.of(context);
    final theme = Theme.of(context);
    final summary = activity.summary;
    final response = summary.invitationResponse;
    final transport = activity.transport;

    String when(DateTime value) => '${material.formatMediumDate(value)} · '
        '${material.formatTimeOfDay(TimeOfDay.fromDateTime(value))}';

    Widget row(IconData icon, String label, String value) => ListTile(
          dense: true,
          contentPadding: EdgeInsets.zero,
          leading: Icon(icon),
          title: Text(label),
          subtitle: Text(value),
        );

    final notice = switch (summary.status) {
      ActivityStatus.cancelled => strings.activityCancelledNotice,
      _ when activity.invitationId == null => strings.notInvitedNotice,
      _ when DateTime.now().isAfter(summary.startsAt) =>
        strings.activityPastNotice,
      _ when activity.deadlinePassed => strings.deadlinePassedNotice,
      _ when summary.needsReconfirmation => strings.reconfirmNotice,
      _ => null,
    };

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(summary.title, style: theme.textTheme.headlineSmall),
        if (notice != null)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Card(
              color: theme.colorScheme.secondaryContainer,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(notice),
              ),
            ),
          ),
        const SizedBox(height: 8),
        row(Icons.event, strings.startsLabel, when(summary.startsAt)),
        if (activity.endsAt != null)
          row(Icons.event_available, strings.endsLabel, when(activity.endsAt!)),
        if (activity.meetingAt != null)
          row(Icons.groups, strings.meetingLabel, when(activity.meetingAt!)),
        if (summary.place?.isNotEmpty ?? false)
          row(Icons.place, strings.placeLabel, summary.place!),
        if (activity.uniform != null)
          row(Icons.checkroom, strings.uniform, activity.uniform!),
        if (activity.responseDeadline != null)
          row(Icons.schedule, strings.deadlineLabel,
              when(activity.responseDeadline!)),
        if (transport != null)
          row(
            Icons.directions_bus,
            strings.transport,
            [
              transport.label,
              if (transport.meetingPoint != null)
                '${strings.meetingPointLabel}: ${transport.meetingPoint}',
              if (transport.departureAt != null)
                '${strings.departureLabel}: ${when(transport.departureAt!)}',
              if (transport.driverName != null)
                '${strings.driverLabel}: ${transport.driverName}',
            ].join('\n'),
          ),
        if (summary.isMandatory)
          row(Icons.priority_high, strings.mandatoryActivity,
              strings.mandatoryActivityExplanation),
        if (activity.description != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(activity.description!),
          ),
        if (activity.programme.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(strings.programme, style: theme.textTheme.titleMedium),
          ...activity.programme.map((item) => ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text(item.title),
              subtitle: item.notes == null ? null : Text(item.notes!))),
        ],
        if (activity.invitationId != null) ...[
          const SizedBox(height: 16),
          Text(strings.yourResponse, style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Chip(
            key: const Key('current-response'),
            avatar: Icon(switch (response) {
              InvitationResponse.accepted => Icons.check_circle,
              InvitationResponse.declined => Icons.cancel,
              InvitationResponse.pending => Icons.help_outline,
            }),
            label: Text(strings.responseName(response)),
          ),
          if (activity.responseNote != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text('${strings.absenceReason}: ${activity.responseNote}'),
            ),
          if (activity.canRespond) ...[
            const SizedBox(height: 12),
            SegmentedButton<InvitationResponse>(
              key: const Key('response-buttons'),
              emptySelectionAllowed: true,
              segments: [
                ButtonSegment(
                  value: InvitationResponse.accepted,
                  icon: const Icon(Icons.check),
                  label: Text(strings.accept),
                ),
                ButtonSegment(
                  value: InvitationResponse.declined,
                  icon: const Icon(Icons.close),
                  label: Text(strings.decline),
                ),
              ],
              selected: {
                if (response != InvitationResponse.pending) response,
              },
              onSelectionChanged: sending
                  ? null
                  : (selection) {
                      if (selection.isEmpty) return;
                      selection.single == InvitationResponse.accepted
                          ? onAccept()
                          : onDecline();
                    },
            ),
            if (sending)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: LinearProgressIndicator(),
              ),
          ],
        ],
      ],
    );
  }
}

/// Pide el motivo de una ausencia. Es dueño de su campo de texto, que sigue en
/// pantalla durante la animación de cierre y no puede liberarse antes.
class _AbsenceReasonDialog extends StatefulWidget {
  const _AbsenceReasonDialog();

  @override
  State<_AbsenceReasonDialog> createState() => _AbsenceReasonDialogState();
}

class _AbsenceReasonDialogState extends State<_AbsenceReasonDialog> {
  final controller = TextEditingController();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return AlertDialog(
      title: Text(strings.absenceReason),
      content: TextField(
        controller: controller,
        autofocus: true,
        maxLength: 500,
        maxLines: 3,
        decoration: InputDecoration(
          labelText: strings.absenceReason,
          helperText: strings.reasonRequired,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(strings.cancel),
        ),
        FilledButton(
          onPressed: () {
            final value = controller.text.trim();
            if (value.isNotEmpty) Navigator.pop(context, value);
          },
          child: Text(strings.submitAbsence),
        ),
      ],
    );
  }
}
