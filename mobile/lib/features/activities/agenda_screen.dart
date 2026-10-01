import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import '../notifications/notification_activation_screen.dart';
import '../notifications/notification_service.dart';
import '../polls/polls_screen.dart';
import 'activity_detail_screen.dart';

class AgendaScreen extends StatefulWidget {
  const AgendaScreen({super.key, required this.controller});
  final AppController controller;
  @override
  State<AgendaScreen> createState() => _AgendaScreenState();
}

class _AgendaScreenState extends State<AgendaScreen> {
  late Future<AgendaSnapshot> future;

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

  @override
  Widget build(BuildContext context) {
    final association = widget.controller.activeAssociation!;
    final strings = AppStrings.of(context);
    final materialStrings = MaterialLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(association.name), actions: [
        IconButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => PollsScreen(
                      association: association,
                      repository: widget.controller.pollsRepository,
                    ))),
            tooltip: strings.polls,
            icon: const Icon(Icons.how_to_vote)),
        IconButton(
            onPressed: widget.controller.changeAssociation,
            tooltip: strings.changeAssociation,
            icon: const Icon(Icons.swap_horiz)),
        const LanguageMenu(),
        IconButton(
            onPressed: widget.controller.logout,
            tooltip: strings.signOut,
            icon: const Icon(Icons.logout)),
      ]),
      body: Column(children: [
        ListenableBuilder(
          listenable: widget.controller.notifications,
          builder: (context, _) {
            final state = widget.controller.notifications.state;
            if (!state.available ||
                state.nextAction == NotificationAction.none) {
              return const SizedBox.shrink();
            }
            return MaterialBanner(
              key: const Key('notifications-pending-banner'),
              leading: const Icon(Icons.notifications_off_outlined),
              content: Text(strings.notificationsPendingBanner),
              actions: [
                TextButton(
                  onPressed: _openNotificationStep,
                  child: Text(strings.review),
                ),
              ],
            );
          },
        ),
        Expanded(
            child: FutureBuilder<AgendaSnapshot>(
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
                        onPressed: reload, child: Text(strings.retry)),
                  ],
                ),
              );
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final agenda = snapshot.data!;
            final items = agenda.activities;
            final offline = agenda.cachedAt == null
                ? null
                : Card(
                    key: const Key('offline-agenda'),
                    margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: ListTile(
                      leading: const Icon(Icons.cloud_off),
                      title: Text(strings.offlineAgenda(
                        '${materialStrings.formatMediumDate(agenda.cachedAt!)} · '
                        '${materialStrings.formatTimeOfDay(TimeOfDay.fromDateTime(agenda.cachedAt!))}',
                      )),
                      trailing: TextButton(
                          onPressed: reload, child: Text(strings.retry)),
                    ),
                  );
            final header = offline == null ? 0 : 1;
            if (items.isEmpty) {
              return RefreshIndicator(
                onRefresh: reload,
                child: ListView(children: [
                  if (offline != null) offline,
                  const SizedBox(height: 120),
                  Center(child: Text(strings.emptyAgenda)),
                ]),
              );
            }
            return RefreshIndicator(
              onRefresh: reload,
              child: ListView.builder(
                itemCount: items.length + header,
                itemBuilder: (_, position) {
                  if (position < header) return offline!;
                  final item = items[position - header];
                  final reply = item.needsReconfirmation
                      ? strings.reconfirmNotice
                      : strings.responseName(item.invitationResponse);
                  return ListTile(
                    leading: Icon(switch (item.invitationResponse) {
                      _ when item.needsReconfirmation => Icons.error_outline,
                      InvitationResponse.accepted => Icons.check_circle,
                      InvitationResponse.declined => Icons.cancel,
                      InvitationResponse.pending => Icons.help_outline,
                    }),
                    title: Text(item.title),
                    subtitle: Text(
                      '${materialStrings.formatMediumDate(item.startsAt)} · '
                      '${materialStrings.formatTimeOfDay(TimeOfDay.fromDateTime(item.startsAt))}'
                      '\n$reply',
                    ),
                    isThreeLine: true,
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => ActivityDetailScreen(
                              association: association,
                              activityId: item.id,
                              repository:
                                  widget.controller.activitiesRepository,
                            ))),
                  );
                },
              ),
            );
          },
        )),
      ]),
    );
  }
}
