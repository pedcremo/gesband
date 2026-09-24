import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';

class PollDetailScreen extends StatefulWidget {
  const PollDetailScreen({
    super.key,
    required this.association,
    required this.pollId,
    required this.repository,
  });
  final Association association;
  final String pollId;
  final PollsRepository repository;
  @override
  State<PollDetailScreen> createState() => _PollDetailScreenState();
}

class _PollDetailScreenState extends State<PollDetailScreen> {
  late Future<Poll> future;
  // Solo vive mientras se elige; tras votar se olvida. Ver `Poll`.
  String? selected;
  bool sending = false;

  @override
  void initState() {
    super.initState();
    future = _load();
  }

  Future<Poll> _load() =>
      widget.repository.getById(widget.association.id, widget.pollId);

  Future<void> _vote(Poll poll) async {
    final strings = AppStrings.of(context);
    final option = poll.choices.firstWhere((item) => item.id == selected);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(strings.pollConfirmTitle),
        content: Text(strings.pollConfirmBody(option.label)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(strings.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(strings.pollConfirm),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => sending = true);
    String? message;
    Poll? updated;
    try {
      updated = await widget.repository
          .vote(widget.association.id, widget.pollId, option.id);
    } on AlreadyVotedException {
      message = strings.pollAlreadyVoted;
    } catch (_) {
      message = strings.pollVoteFailed;
    }
    if (!mounted) return;
    setState(() {
      sending = false;
      selected = null;
      future = updated != null ? Future.value(updated) : _load();
    });
    if (message != null) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(strings.poll)),
      body: FutureBuilder<Poll>(
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
                    onPressed: () => setState(() => future = _load()),
                    child: Text(strings.retry),
                  ),
                ],
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return _body(context, strings, snapshot.data!);
        },
      ),
    );
  }

  Widget _body(BuildContext context, AppStrings strings, Poll poll) {
    final materialStrings = MaterialLocalizations.of(context);
    final closes = '${materialStrings.formatMediumDate(poll.closesAt)} '
        '${materialStrings.formatTimeOfDay(TimeOfDay.fromDateTime(poll.closesAt))}';
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(poll.question, style: theme.textTheme.headlineSmall),
        if (poll.description != null) ...[
          const SizedBox(height: 8),
          Text(poll.description!),
        ],
        const SizedBox(height: 12),
        _statusBanner(strings, poll, closes),
        const SizedBox(height: 16),
        if (poll.canVote) ...[
          Text(strings.pollChooseOption, style: theme.textTheme.titleMedium),
          RadioGroup<String>(
            groupValue: selected,
            onChanged: (value) => setState(() => selected = value),
            child: Column(
              children: [
                for (final choice in poll.choices)
                  RadioListTile<String>(
                    value: choice.id,
                    title: Text(choice.label),
                    enabled: !sending,
                  ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: selected == null || sending ? null : () => _vote(poll),
            icon: const Icon(Icons.how_to_vote),
            label: Text(strings.pollVote),
          ),
          const SizedBox(height: 8),
          Text(strings.pollAnonymousNote, style: theme.textTheme.bodySmall),
          const SizedBox(height: 16),
        ],
        if (poll.results != null) _results(strings, poll, poll.results!),
      ],
    );
  }

  Widget _statusBanner(AppStrings strings, Poll poll, String closes) {
    final (IconData icon, String title, String? detail) = switch (poll) {
      Poll(status: PollStatus.cancelled) => (
          Icons.block,
          strings.pollCancelled,
          poll.cancelReason == null
              ? null
              : '${strings.reason}: ${poll.cancelReason}'
        ),
      Poll(status: PollStatus.published) => (
          Icons.verified,
          strings.pollPublished,
          null
        ),
      _ when poll.awaitingPublication(DateTime.now()) => (
          Icons.hourglass_bottom,
          strings.pollAwaitingPublication,
          null
        ),
      _ => (
          poll.canVote ? Icons.how_to_vote : Icons.check_circle,
          poll.hasVoted == true ? strings.pollVoted : strings.pollOpen,
          strings.pollClosesAt(closes)
        ),
    };
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        subtitle: detail == null ? null : Text(detail),
      ),
    );
  }

  Widget _results(AppStrings strings, Poll poll, PollResults results) {
    final total = results.votesCast;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          results.kind == PollResultKind.finalResult
              ? strings.pollFinal
              : strings.pollProvisional,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        for (final row in results.options) ...[
          Row(
            children: [
              Expanded(child: Text(row.label)),
              Text(strings.pollOptionVotes(row.votes,
                  total == 0 ? 0 : (row.votes * 100 / total).round())),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: total == 0 ? 0 : row.votes / total,
            minHeight: 8,
            semanticsLabel: row.label,
          ),
          const SizedBox(height: 12),
        ],
        Text(strings.pollVotesCast(total, poll.recipients),
            style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
