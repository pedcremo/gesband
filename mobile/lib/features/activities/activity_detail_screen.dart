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

  @override
  void initState() {
    super.initState();
    future =
        widget.repository.getById(widget.association.id, widget.activityId);
  }

  Future<void> send(InvitationResponse value, {String note = ''}) async {
    try {
      final result = await widget.repository
          .respond(widget.association.id, widget.activityId, value, note: note);
      if (!mounted) return;
      setState(() => future = Future.value(result));
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppStrings.of(context).genericError)));
    }
  }

  Future<void> declineMandatory() async {
    final strings = AppStrings.of(context);
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
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
      ),
    );
    controller.dispose();
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
                    onPressed: () => setState(() => future = widget.repository
                        .getById(widget.association.id, widget.activityId)),
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
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Text(activity.summary.title,
                  style: Theme.of(context).textTheme.headlineSmall),
              if (activity.description != null) Text(activity.description!),
              if (activity.uniform?.isNotEmpty ?? false)
                ListTile(
                    leading: const Icon(Icons.checkroom),
                    title: Text(strings.uniform),
                    subtitle: Text(activity.uniform!)),
              if (activity.transport != null)
                ListTile(
                    leading: const Icon(Icons.directions_car),
                    title: Text(strings.transport),
                    subtitle: Text(activity.transport!.mode)),
              if (activity.summary.isMandatory)
                ListTile(
                  leading: const Icon(Icons.priority_high),
                  title: Text(strings.mandatoryActivity),
                  subtitle: Text(strings.mandatoryActivityExplanation),
                ),
              const SizedBox(height: 16),
              Text(strings.programme,
                  style: TextStyle(fontWeight: FontWeight.bold)),
              ...activity.programme.map((item) => ListTile(
                  title: Text(item.title),
                  subtitle: item.notes == null ? null : Text(item.notes!))),
              const SizedBox(height: 16),
              Text(strings.response,
                  style: TextStyle(fontWeight: FontWeight.bold)),
              Row(children: [
                Expanded(
                    child: OutlinedButton(
                        onPressed: activity.summary.isMandatory
                            ? declineMandatory
                            : () => send(InvitationResponse.declined),
                        child: Text(strings.decline))),
                const SizedBox(width: 8),
                Expanded(
                    child: FilledButton(
                        onPressed: () => send(InvitationResponse.accepted),
                        child: Text(strings.accept))),
              ]),
            ],
          );
        },
      ),
    );
  }
}
