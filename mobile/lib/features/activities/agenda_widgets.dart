import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/theme/visual_style.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';

/// Píldora y tono de la respuesta propia a una actividad.
(String, Tone) responsePill(AppStrings strings, ActivitySummary item) =>
    switch (item) {
      ActivitySummary(status: ActivityStatus.cancelled) => (
          strings.pillCancelled,
          Tone.neutral
        ),
      ActivitySummary(needsReconfirmation: true) => (
          strings.pillReconfirm,
          Tone.warning
        ),
      ActivitySummary(invitationResponse: InvitationResponse.accepted) => (
          strings.pillGoing,
          Tone.success
        ),
      ActivitySummary(invitationResponse: InvitationResponse.declined) => (
          strings.pillNotGoing,
          Tone.danger
        ),
      _ => (strings.pillReply, Tone.warning),
    };

/// La actividad espera una respuesta de la persona.
bool awaitsReply(ActivitySummary item, DateTime now) =>
    item.canRespondAt(now) &&
    (item.needsReconfirmation ||
        item.invitationResponse == InvitationResponse.pending);

/// Cartel de la próxima convocatoria.
class ActivityPoster extends StatelessWidget {
  const ActivityPoster({
    super.key,
    required this.item,
    required this.canRespond,
    required this.sending,
    required this.onOpen,
    required this.onRespond,
  });

  final ActivitySummary item;
  final bool canRespond;
  final bool sending;
  final VoidCallback onOpen;
  final ValueChanged<InvitationResponse> onRespond;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    return switch (t.style) {
      VisualStyle.escenario => _escenario(context, t),
      VisualStyle.partitura => _partitura(context, t),
      VisualStyle.festa => _festa(context, t),
    };
  }

  List<(String, String)> _facts(AppStrings strings, DateLabels dates) => [
        if (item.meetingAt != null)
          (strings.meetingLabel, dates.time(item.meetingAt!))
        else
          (strings.startsLabel, dates.time(item.startsAt)),
        if (item.place != null) (strings.placeLabel, item.place!),
        if (item.uniform != null) (strings.uniform, item.uniform!),
        if (item.transportLabel != null)
          (strings.transport, item.transportLabel!),
      ];

  Widget _escenario(BuildContext context, GesbandTokens t) {
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme;
    final ink = t.onPrimary;
    return MergeSemantics(
      child: Material(
        key: const Key('next-activity'),
        color: t.primary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(t.radiusLarge),
          side: t.primaryEdgeSide,
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onOpen,
          child: Stack(
            children: [
              Positioned(
                right: -10,
                top: -28,
                child: ExcludeSemantics(
                  child: Opacity(
                    opacity: 0.16,
                    child: Text(
                      '${item.startsAt.day}',
                      textScaler: TextScaler.noScaling,
                      style: t.display(170, color: ink).copyWith(height: 1),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(GesbandSpacing.xl),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Eyebrow(strings.nextActivity(dates.longDay(item.startsAt)),
                        color: ink),
                    const SizedBox(height: GesbandSpacing.md),
                    Padding(
                      padding: const EdgeInsets.only(right: 48),
                      child: DisplayText(item.title, size: 40, color: ink),
                    ),
                    const SizedBox(height: GesbandSpacing.lg),
                    _FactGrid(
                      facts: _facts(strings, dates),
                      labelStyle: text.bodySmall!.copyWith(color: ink),
                      valueStyle: text.titleMedium!
                          .copyWith(color: ink, fontWeight: FontWeight.w700),
                    ),
                    if (canRespond) ...[
                      const SizedBox(height: GesbandSpacing.lg),
                      _ReplyButtons(
                        response: item.invitationResponse,
                        sending: sending,
                        onRespond: onRespond,
                        filledBackground: ink,
                        filledForeground: t.primaryOnInk,
                        outlineColor: ink,
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _partitura(BuildContext context, GesbandTokens t) {
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme;
    final details = _facts(strings, dates).map((f) => '${f.$1}: ${f.$2}');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Eyebrow(strings.nextActivity(dates.longDay(item.startsAt))),
        const SizedBox(height: GesbandSpacing.md),
        SurfaceCard(
          key: const Key('next-activity'),
          onTap: onOpen,
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              MergeSemantics(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _DateColumn(date: item.startsAt, accent: t.primaryText),
                    const SizedBox(width: GesbandSpacing.lg),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          DisplayText(item.title, size: 20),
                          const SizedBox(height: GesbandSpacing.xs),
                          for (final line in details)
                            Text(line,
                                style:
                                    text.bodyMedium!.copyWith(color: t.muted)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              if (canRespond) ...[
                const SizedBox(height: 14),
                _ReplyButtons(
                  response: item.invitationResponse,
                  sending: sending,
                  onRespond: onRespond,
                ),
              ],
              if (item.responseDeadline != null) ...[
                const SizedBox(height: GesbandSpacing.sm),
                Text(
                  '${strings.deadlineLabel} ${dates.dateTime(item.responseDeadline!)}',
                  style: text.bodySmall,
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Widget _festa(BuildContext context, GesbandTokens t) {
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme;
    final details = [
      dates.time(item.meetingAt ?? item.startsAt),
      if (item.place != null) item.place!,
      if (item.transportLabel != null) item.transportLabel!,
      if (item.uniform != null) item.uniform!,
    ].join(' · ');
    return SurfaceCard(
      key: const Key('next-activity'),
      onTap: onOpen,
      padding: const EdgeInsets.all(6),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _TicketDate(date: item.startsAt, highlighted: true),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Eyebrow(strings.nextActivity(dates.longDay(item.startsAt)),
                        color: t.primaryText),
                    const SizedBox(height: 6),
                    DisplayText(item.title, size: 19),
                    const SizedBox(height: 6),
                    Text(details,
                        style: text.bodyMedium!.copyWith(color: t.muted)),
                    if (canRespond) ...[
                      const SizedBox(height: GesbandSpacing.sm),
                      _ReplyButtons(
                        response: item.invitationResponse,
                        sending: sending,
                        onRespond: onRespond,
                        outlineColor: Colors.transparent,
                        secondaryBackground: t.surfaceMuted,
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Fila de una actividad en la lista por meses.
class ActivityRow extends StatelessWidget {
  const ActivityRow({
    super.key,
    required this.item,
    required this.highlighted,
    required this.onOpen,
  });

  final ActivitySummary item;

  /// Pide respuesta: se resalta con el color secundario.
  final bool highlighted;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme;
    final (pillLabel, tone) = responsePill(strings, item);
    final subtitle = [
      // En Festa el día de la semana ya está en el bloque de fecha.
      if (t.style != VisualStyle.festa) dates.weekdayShort(item.startsAt),
      dates.time(item.startsAt),
      if (item.place != null) item.place!,
      if (item.transportLabel != null) item.transportLabel!,
    ].join(' · ');
    final titleStyle = t.style == VisualStyle.festa
        ? t.display(17)
        : text.titleMedium!.copyWith(fontSize: 15);
    final body = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(item.title, style: titleStyle),
        const SizedBox(height: 2),
        Text(subtitle, style: text.bodySmall),
      ],
    );
    final pill = StatusPill(label: pillLabel, tone: tone);

    return MergeSemantics(
      child: switch (t.style) {
        VisualStyle.escenario => SurfaceCard(
            onTap: onOpen,
            borderColor: highlighted ? t.highlight : null,
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Row(
              children: [
                ConstrainedBox(
                  constraints: const BoxConstraints(minWidth: 44),
                  child: Text('${item.startsAt.day}',
                      style: t.display(34).copyWith(height: 1)),
                ),
                const SizedBox(width: 14),
                Expanded(child: body),
                const SizedBox(width: GesbandSpacing.sm),
                pill,
              ],
            ),
          ),
        VisualStyle.partitura => InkWell(
            onTap: onOpen,
            child: Container(
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(color: t.line),
                  left: highlighted
                      ? BorderSide(color: t.highlight, width: 3)
                      : BorderSide.none,
                ),
              ),
              constraints:
                  const BoxConstraints(minHeight: GesbandSpacing.minTarget),
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Row(
                children: [
                  SizedBox(
                    width: 52,
                    child: Text('${item.startsAt.day}',
                        textAlign: TextAlign.center, style: t.display(22)),
                  ),
                  const SizedBox(width: GesbandSpacing.lg),
                  Expanded(child: body),
                  const SizedBox(width: GesbandSpacing.sm),
                  pill,
                ],
              ),
            ),
          ),
        VisualStyle.festa => SurfaceCard(
            onTap: onOpen,
            borderColor: highlighted ? t.highlight : null,
            padding: const EdgeInsets.all(6),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _TicketDate(date: item.startsAt, highlighted: highlighted),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          body,
                          const SizedBox(height: 6),
                          pill,
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
      },
    );
  }
}

class _FactGrid extends StatelessWidget {
  const _FactGrid({
    required this.facts,
    required this.labelStyle,
    required this.valueStyle,
  });

  final List<(String, String)> facts;
  final TextStyle labelStyle;
  final TextStyle valueStyle;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final width = (constraints.maxWidth - 10) / 2;
          return Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              for (final (label, value) in facts)
                SizedBox(
                  width: width,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(label, style: labelStyle),
                      const SizedBox(height: 2),
                      Text(value, style: valueStyle),
                    ],
                  ),
                ),
            ],
          );
        },
      );
}

class _ReplyButtons extends StatelessWidget {
  const _ReplyButtons({
    required this.response,
    required this.sending,
    required this.onRespond,
    this.filledBackground,
    this.filledForeground,
    this.outlineColor,
    this.secondaryBackground,
  });

  final InvitationResponse response;
  final bool sending;
  final ValueChanged<InvitationResponse> onRespond;
  final Color? filledBackground;
  final Color? filledForeground;
  final Color? outlineColor;
  final Color? secondaryBackground;

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final t = GesbandTokens.of(context);
    final accepted = response == InvitationResponse.accepted;
    final declined = response == InvitationResponse.declined;
    final attend = FilledButton(
      key: const Key('poster-accept'),
      style: FilledButton.styleFrom(
        backgroundColor: filledBackground,
        foregroundColor: filledForeground,
      ),
      onPressed: sending || accepted
          ? null
          : () => onRespond(InvitationResponse.accepted),
      child: _label(strings.attendShort, accepted),
    );
    final decline = OutlinedButton(
      key: const Key('poster-decline'),
      style: OutlinedButton.styleFrom(
        foregroundColor:
            outlineColor == Colors.transparent ? t.ink : outlineColor ?? t.ink,
        backgroundColor: secondaryBackground,
        side: outlineColor == null
            ? null
            : BorderSide(
                color: outlineColor!,
                width: outlineColor == Colors.transparent ? 0 : 2),
      ),
      onPressed: sending || declined
          ? null
          : () => onRespond(InvitationResponse.declined),
      child: _label(strings.declineShort, declined),
    );
    return Row(
      children: [
        Expanded(child: attend),
        const SizedBox(width: 10),
        Expanded(child: decline),
      ],
    );
  }

  Widget _label(String text, bool chosen) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (chosen) ...[
            const Icon(Icons.check, size: 18),
            const SizedBox(width: 4),
          ],
          Flexible(child: Text(text, textAlign: TextAlign.center)),
        ],
      );
}

class _DateColumn extends StatelessWidget {
  const _DateColumn({required this.date, required this.accent});

  final DateTime date;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme;
    return SizedBox(
      width: 52,
      child: Column(
        children: [
          Text(dates.monthShort(date).toUpperCase(),
              style: text.labelSmall!.copyWith(color: accent)),
          Text('${date.day}', style: t.display(34).copyWith(height: 1)),
          Text(dates.weekdayShort(date), style: text.bodySmall),
        ],
      ),
    );
  }
}

/// Bloque de fecha de las tarjetas tipo entrada de Festa.
class _TicketDate extends StatelessWidget {
  const _TicketDate({required this.date, required this.highlighted});

  final DateTime date;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    final t = GesbandTokens.of(context);
    final dates = DateLabels.of(context);
    final text = Theme.of(context).textTheme.labelSmall!;
    final ink = highlighted ? t.onPrimaryTint : t.muted;
    return Container(
      width: 72,
      padding: const EdgeInsets.symmetric(vertical: GesbandSpacing.sm),
      decoration: BoxDecoration(
        color: highlighted ? t.primaryTint : t.surfaceMuted,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(dates.weekdayShort(date).toUpperCase(),
              style: text.copyWith(color: ink)),
          Text('${date.day}',
              style: t
                  .display(32, color: highlighted ? t.onPrimaryTint : t.ink)
                  .copyWith(height: 1)),
          Text(dates.monthShort(date).toUpperCase(),
              style: text.copyWith(color: ink)),
        ],
      ),
    );
  }
}
