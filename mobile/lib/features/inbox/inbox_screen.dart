import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/app_controller.dart';
import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/theme_controller.dart';
import '../../core/ui/brand_header.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';
import '../notifications/push_gateway.dart';

/// Avisos persistentes de la cuenta. Al abrir uno se marca como leído y, si
/// trata de una actividad o encuesta, se abre esa pantalla.
class InboxScreen extends StatefulWidget {
  const InboxScreen({super.key, required this.controller});

  final AppController controller;

  @override
  State<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends State<InboxScreen> {
  late Future<List<InboxNotification>> future;
  final read = <String>{};

  @override
  void initState() {
    super.initState();
    future = widget.controller.inboxRepository.list();
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

  Future<void> reload() async {
    setState(() {
      future = widget.controller.inboxRepository.list();
    });
    await future;
  }

  void _open(InboxNotification item) {
    if (!item.isRead && !read.contains(item.id)) {
      setState(() => read.add(item.id));
      // Marcar como leído no debe impedir abrir el aviso si falla la red.
      unawaited(widget.controller.inboxRepository
          .markRead(item.id)
          .catchError((Object _) {}));
    }
    final target = item.pollId != null
        ? PollTarget(item.pollId!)
        : item.activityId != null
            ? ActivityTarget(item.activityId!)
            : null;
    if (target != null) widget.controller.openTarget(target);
  }

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return FutureBuilder<List<InboxNotification>>(
      future: future,
      builder: (context, snapshot) {
        final children = <Widget>[
          BrandHeader(
            brand: ThemeScope.brandOf(context),
            title: strings.inbox,
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
              icon: Icons.notifications_none_rounded,
              message: strings.emptyInbox,
            ),
          ));
        } else {
          for (final item in snapshot.data!) {
            children.add(Padding(
              padding: const EdgeInsets.fromLTRB(
                  GesbandSpacing.xl, GesbandSpacing.md, GesbandSpacing.xl, 0),
              child: _InboxCard(
                item: item,
                unread: !item.isRead && !read.contains(item.id),
                onOpen: () => _open(item),
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
  }
}

class _InboxCard extends StatelessWidget {
  const _InboxCard({
    required this.item,
    required this.unread,
    required this.onOpen,
  });

  final InboxNotification item;
  final bool unread;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final strings = AppStrings.of(context);
    final text = Theme.of(context).textTheme;
    return MergeSemantics(
      child: SurfaceCard(
        onTap: onOpen,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 6, right: GesbandSpacing.md),
              child: Semantics(
                label: unread ? strings.unread : null,
                child: Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: unread ? t.primaryText : t.line,
                  ),
                ),
              ),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    style: text.titleMedium!.copyWith(
                      fontWeight: unread ? FontWeight.w700 : FontWeight.w600,
                    ),
                  ),
                  if (item.body.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(item.body, style: text.bodyMedium),
                  ],
                  const SizedBox(height: GesbandSpacing.xs),
                  Text(DateLabels.of(context).dateTime(item.createdAt),
                      style: text.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
