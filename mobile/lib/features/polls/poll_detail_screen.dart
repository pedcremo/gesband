import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';

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
      appBar: ScreenBar(title: strings.poll),
      body: FutureBuilder<Poll>(
        future: future,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return MessageView(
              icon: Icons.cloud_off_rounded,
              tone: Tone.danger,
              message: strings.genericError,
              actionLabel: strings.retry,
              onAction: () => setState(() {
                future = _load();
              }),
            );
          }
          if (!snapshot.hasData) return const LoadingView();
          return _body(context, strings, snapshot.data!);
        },
      ),
    );
  }

  Widget _body(BuildContext context, AppStrings strings, Poll poll) {
    final closes = DateLabels.of(context).dateTime(poll.closesAt);
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(
          GesbandSpacing.xl, GesbandSpacing.sm, GesbandSpacing.xl, 40),
      children: [
        Semantics(header: true, child: DisplayText(poll.question, size: 32)),
        if (poll.description != null) ...[
          const SizedBox(height: GesbandSpacing.sm),
          Text(poll.description!, style: text.bodyLarge),
        ],
        const SizedBox(height: GesbandSpacing.lg),
        _statusBanner(strings, poll, closes),
        const SizedBox(height: GesbandSpacing.xl),
        if (poll.canVote) ...[
          Text(strings.pollChooseOption, style: text.titleMedium),
          const SizedBox(height: GesbandSpacing.sm),
          RadioGroup<String>(
            groupValue: selected,
            onChanged: (value) => setState(() => selected = value),
            child: Column(
              children: [
                for (final choice in poll.choices)
                  Padding(
                    padding: const EdgeInsets.only(bottom: GesbandSpacing.sm),
                    child: RadioListTile<String>(
                      value: choice.id,
                      title: Text(choice.label, style: text.titleMedium),
                      enabled: !sending,
                      tileColor: t.surface,
                      selectedTileColor: t.primaryTint,
                      selected: selected == choice.id,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(t.radiusCard),
                        side: BorderSide(
                          color: selected == choice.id ? t.primaryText : t.line,
                          width: selected == choice.id ? 2 : 1,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: GesbandSpacing.sm),
          FilledButton.icon(
            onPressed: selected == null || sending ? null : () => _vote(poll),
            icon: const Icon(Icons.how_to_vote),
            label: Text(strings.pollVote),
          ),
          const SizedBox(height: GesbandSpacing.sm),
          Row(
            children: [
              Icon(Icons.lock_outline_rounded, size: 16, color: t.muted),
              const SizedBox(width: GesbandSpacing.xs),
              Expanded(
                child: Text(strings.pollAnonymousNote, style: text.bodySmall),
              ),
            ],
          ),
          const SizedBox(height: GesbandSpacing.xl),
        ],
        if (poll.results != null) _results(strings, poll, poll.results!),
      ],
    );
  }

  Widget _statusBanner(AppStrings strings, Poll poll, String closes) {
    final (IconData icon, String title, String? detail, Tone tone) =
        switch (poll) {
      Poll(status: PollStatus.cancelled) => (
          Icons.block,
          strings.pollCancelled,
          poll.cancelReason == null
              ? null
              : '${strings.reason}: ${poll.cancelReason}',
          Tone.danger,
        ),
      Poll(status: PollStatus.published) => (
          Icons.verified,
          strings.pollPublished,
          null,
          Tone.brand,
        ),
      _ when poll.awaitingPublication(DateTime.now()) => (
          Icons.hourglass_bottom,
          strings.pollAwaitingPublication,
          null,
          Tone.neutral,
        ),
      _ => (
          poll.canVote ? Icons.how_to_vote : Icons.check_circle,
          poll.hasVoted == true ? strings.pollVoted : strings.pollOpen,
          strings.pollClosesAt(closes),
          poll.hasVoted == true ? Tone.success : Tone.warning,
        ),
    };
    final t = GesbandTokens.of(context);
    final colors = toneColors(t, tone);
    final text = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(GesbandSpacing.lg),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(t.radiusCard),
      ),
      child: Row(
        children: [
          Icon(icon, color: colors.ink),
          const SizedBox(width: GesbandSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: text.titleMedium!.copyWith(color: colors.ink)),
                if (detail != null)
                  Text(detail,
                      style: text.bodyMedium!.copyWith(color: colors.ink)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _results(AppStrings strings, Poll poll, PollResults results) {
    final total = results.votesCast;
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionTitle(results.kind == PollResultKind.finalResult
              ? strings.pollFinal
              : strings.pollProvisional),
          const SizedBox(height: GesbandSpacing.md),
          for (final row in results.options) ...[
            Row(
              children: [
                Expanded(child: Text(row.label, style: text.titleSmall)),
                Text(
                  strings.pollOptionVotes(row.votes,
                      total == 0 ? 0 : (row.votes * 100 / total).round()),
                  style: text.labelMedium!.copyWith(color: t.muted),
                ),
              ],
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: total == 0 ? 0 : row.votes / total,
                minHeight: 10,
                color: t.primaryText,
                semanticsLabel: row.label,
              ),
            ),
            const SizedBox(height: GesbandSpacing.md),
          ],
          Text(strings.pollVotesCast(total, poll.recipients),
              style: text.bodySmall),
        ],
      ),
    );
  }
}
