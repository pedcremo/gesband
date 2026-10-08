import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/repositories/repositories.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/theme/visual_style.dart';
import '../../core/ui/brand_header.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';
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
    setState(() {
      future = _load();
    });
    await future;
  }

  (String, Tone) _status(AppStrings strings, Poll poll) {
    if (poll.status == PollStatus.cancelled) {
      return (strings.pollCancelled, Tone.danger);
    }
    if (poll.status == PollStatus.published) {
      return (strings.pollPublished, Tone.brand);
    }
    if (poll.awaitingPublication(DateTime.now())) {
      return (strings.pollAwaitingPublication, Tone.neutral);
    }
    return poll.canVote
        ? (strings.pollToVote, Tone.warning)
        : (strings.pollVoted, Tone.success);
  }

  Future<void> _open(Poll poll) async {
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => PollDetailScreen(
        association: widget.association,
        pollId: poll.id,
        repository: widget.repository,
      ),
    ));
    if (mounted) await reload();
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    // En la navegación principal lleva la cabecera de la banda; si se abre
    // encima de otra pantalla, barra con botón de volver.
    final embedded = !Navigator.of(context).canPop();
    final list = FutureBuilder<List<Poll>>(
      future: future,
      builder: (context, snapshot) {
        final children = <Widget>[
          if (embedded)
            BrandHeader(
              brand: ThemeScope.brandOf(context),
              title: strings.polls,
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
        } else if (snapshot.data!.isEmpty) {
          children.add(SizedBox(
            height: 360,
            child: MessageView(
              icon: Icons.how_to_vote_outlined,
              message: strings.emptyPolls,
            ),
          ));
        } else {
          for (final poll in snapshot.data!) {
            children.add(Padding(
              padding: const EdgeInsets.fromLTRB(
                  GesbandSpacing.xl, GesbandSpacing.md, GesbandSpacing.xl, 0),
              child: _PollCard(
                poll: poll,
                status: _status(strings, poll),
                onOpen: () => _open(poll),
              ),
            ));
          }
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
    return embedded
        ? list
        : Scaffold(appBar: ScreenBar(title: strings.polls), body: list);
  }
}

class _PollCard extends StatelessWidget {
  const _PollCard({
    required this.poll,
    required this.status,
    required this.onOpen,
  });

  final Poll poll;
  final (String, Tone) status;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme;
    return MergeSemantics(
      child: SurfaceCard(
        onTap: onOpen,
        borderColor: poll.canVote ? t.highlight : null,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  StatusPill(label: status.$1, tone: status.$2),
                  const SizedBox(height: GesbandSpacing.sm),
                  Text(poll.question,
                      style: t.style == VisualStyle.escenario
                          ? text.titleMedium!.copyWith(fontSize: 17)
                          : t.display(19)),
                  if (poll.status == PollStatus.open) ...[
                    const SizedBox(height: GesbandSpacing.xs),
                    Text(strings.pollClosesAt(dates.dateTime(poll.closesAt)),
                        style: text.bodySmall),
                  ],
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: t.muted),
          ],
        ),
      ),
    );
  }
}
