import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/localization/language_menu.dart';
import '../../core/models/models.dart';
import 'activity_detail_screen.dart';

class AgendaScreen extends StatefulWidget {
  const AgendaScreen({super.key, required this.controller});
  final AppController controller;
  @override
  State<AgendaScreen> createState() => _AgendaScreenState();
}

class _AgendaScreenState extends State<AgendaScreen> {
  late Future<List<ActivitySummary>> future;

  @override
  void initState() {
    super.initState();
    future = widget.controller.activitiesRepository
        .listMine(widget.controller.activeAssociation!.id);
  }

  Future<void> reload() async {
    setState(() => future = widget.controller.activitiesRepository
        .listMine(widget.controller.activeAssociation!.id));
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
            onPressed: widget.controller.changeAssociation,
            tooltip: strings.changeAssociation,
            icon: const Icon(Icons.swap_horiz)),
        const LanguageMenu(),
        IconButton(
            onPressed: widget.controller.logout,
            tooltip: strings.signOut,
            icon: const Icon(Icons.logout)),
      ]),
      body: FutureBuilder<List<ActivitySummary>>(
        future: future,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(strings.genericError),
                  const SizedBox(height: 8),
                  OutlinedButton(onPressed: reload, child: Text(strings.retry)),
                ],
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final items = snapshot.data!;
          if (items.isEmpty) {
            return Center(child: Text(strings.emptyAgenda));
          }
          return RefreshIndicator(
            onRefresh: reload,
            child: ListView.builder(
              itemCount: items.length,
              itemBuilder: (_, index) {
                final item = items[index];
                return ListTile(
                  leading: const Icon(Icons.event),
                  title: Text(item.title),
                  subtitle: Text(
                    '${materialStrings.formatMediumDate(item.startsAt)} · '
                    '${materialStrings.formatTimeOfDay(TimeOfDay.fromDateTime(item.startsAt))}',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => ActivityDetailScreen(
                            association: association,
                            activityId: item.id,
                            repository: widget.controller.activitiesRepository,
                          ))),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
