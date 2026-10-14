import 'package:flutter/material.dart';

import '../../core/localization/app_strings.dart';
import '../../core/models/models.dart';
import '../../core/theme/gesband_tokens.dart';
import '../../core/ui/components.dart';
import '../../core/ui/formatting.dart';

/// «Lo que se me debe» en Mi ficha: totales del servidor y la lista de
/// actividades remuneradas con asistencia registrada.
///
/// Las fechas se muestran en la zona del dispositivo, como el resto de la
/// app (ver el informe de la tarea: la zona de la asociación queda pendiente).
class EarningsSection extends StatelessWidget {
  const EarningsSection({
    super.key,
    required this.future,
    required this.onRetry,
  });

  final Future<Earnings> future;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    return FutureBuilder<Earnings>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return InlineNotice(
            key: const Key('earnings-error'),
            icon: Icons.cloud_off_rounded,
            tone: Tone.neutral,
            message: strings.earningsUnavailable,
            actionLabel: strings.retry,
            onAction: onRetry,
          );
        }
        if (snapshot.connectionState != ConnectionState.done ||
            !snapshot.hasData) {
          return const SizedBox(
            key: Key('earnings-loading'),
            height: 96,
            child: LoadingView(),
          );
        }
        final earnings = snapshot.data!;
        if (earnings.isEmpty) {
          return InlineNotice(
            key: const Key('earnings-empty'),
            icon: Icons.euro_rounded,
            tone: Tone.neutral,
            message: strings.earningsEmpty,
          );
        }
        return _EarningsCard(earnings: earnings);
      },
    );
  }
}

class _EarningsCard extends StatelessWidget {
  const _EarningsCard({required this.earnings});

  final Earnings earnings;

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final money = MoneyLabels.of(context);
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    return SurfaceCard(
      key: const Key('earnings-card'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          MergeSemantics(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(strings.owedTotal, style: text.bodySmall),
                DisplayText(
                  money.format(earnings.owedTotal),
                  key: const Key('earnings-owed-total'),
                  size: 40,
                  color: t.primaryText,
                ),
              ],
            ),
          ),
          const SizedBox(height: GesbandSpacing.xs),
          MergeSemantics(
            child: Text(
              '${strings.paidTotal}: ${money.format(earnings.paidTotal)}',
              key: const Key('earnings-paid-total'),
              style: text.titleMedium,
            ),
          ),
          const SizedBox(height: GesbandSpacing.sm),
          Text(strings.earningsExplanation,
              style: text.bodySmall!.copyWith(color: t.muted)),
          const SizedBox(height: GesbandSpacing.sm),
          for (final item in earnings.items) _EarningRow(item: item),
        ],
      ),
    );
  }
}

class _EarningRow extends StatelessWidget {
  const _EarningRow({required this.item});

  final EarningItem item;

  @override
  Widget build(BuildContext context) {
    final strings = AppStrings.of(context);
    final dates = DateLabels.of(context);
    final money = MoneyLabels.of(context);
    final t = GesbandTokens.of(context);
    final text = Theme.of(context).textTheme;
    final paidAt = item.paidAt;
    final (label, tone) = switch (item.status) {
      EarningStatus.owed => (strings.earningOwed, Tone.warning),
      EarningStatus.paid => (
          paidAt == null
              ? strings.earningPaid
              : strings.earningPaidOn(dates.mediumDate(paidAt)),
          Tone.success
        ),
      EarningStatus.unknown => (strings.earningUnknown, Tone.neutral),
    };
    final startsAt = item.activityStartsAt;
    final amount = item.amount;
    return MergeSemantics(
      child: Container(
        key: Key('earning-${item.invitationId}'),
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: t.line)),
        ),
        padding: const EdgeInsets.symmetric(vertical: GesbandSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.activityTitle, style: text.titleMedium),
                  if (startsAt != null)
                    Text(dates.mediumDate(startsAt), style: text.bodySmall),
                  const SizedBox(height: GesbandSpacing.xs),
                  StatusPill(label: label, tone: tone),
                ],
              ),
            ),
            const SizedBox(width: GesbandSpacing.md),
            if (amount != null)
              Text(money.format(amount),
                  style:
                      text.titleMedium!.copyWith(fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }
}
