import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import 'poll_detail_screen.dart';

class PollsScreen extends StatefulWidget {
  const PollsScreen(
      {super.key, required this.association, required this.repository});
  final Association association;
  final PollsRepository repository;
  @override
  State<PollsScreen> createState() => _PollsScreenState();
}

class _PollsScreenState extends State<PollsScreen> {
  late Future<List<Poll>> future;

  @override
  void initState() {
    super.initState();
    future = _load();
  }

  /// Primero las que esperan el voto de la persona; despues, por cierre.
  Future<List<Poll>> _load() async {
    final polls = [...await widget.repository.listMine(widget.association.id)];
    polls.sort((a, b) {
      if (a.canVote != b.canVote) return a.canVote ? -1 : 1;
      return b.closesAt.compareTo(a.closesAt);
    });
    return polls;
  }

  Future<void> reload() async {
    setState(() => future = _load());
    await future;
  }

  String _statusLabel(AppStrings strings, Poll poll) {
    if (poll.status == PollStatus.cancelled) return strings.pollCancelled;
    if (poll.status == PollStatus.published) return strings.pollPublished;
    if (poll.awaitingPublication(DateTime.now())) {
      return strings.pollAwaitingPublication;
    }
    return poll.canVote ? strings.pollToVote : strings.pollVoted;
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(strings.polls)),
      body: FutureBuilder<List<Poll>>(
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
          final polls = snapshot.data!;
          if (polls.isEmpty) return Center(child: Text(strings.emptyPolls));
          return RefreshIndicator(
            onRefresh: reload,
            child: ListView.builder(
              itemCount: polls.length,
              itemBuilder: (_, index) {
                final poll = polls[index];
                return ListTile(
                  leading: Icon(poll.canVote
                      ? Icons.how_to_vote
                      : Icons.how_to_vote_outlined),
                  title: Text(poll.question),
                  subtitle: Text(_statusLabel(strings, poll)),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.of(context).push(MaterialPageRoute<void>(
                      builder: (_) => PollDetailScreen(
                        association: widget.association,
                        pollId: poll.id,
                        repository: widget.repository,
                      ),
                    ));
                    if (mounted) await reload();
                  },
                );
              },
            ),
          );
        },
      ),
    );
  }
}
