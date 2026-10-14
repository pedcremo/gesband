import 'package:flutter_test/flutter_test.dart';

import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/ui/formatting.dart';

import 'support/earnings_fixtures.dart';
import 'support/visual_harness.dart';

void main() {
  group('Money', () {
    test('reads the decimal strings of the API exactly, in cents', () {
      expect(Money.tryParse('25.00'), const Money(2500));
      expect(Money.tryParse('0.10'), const Money(10));
      expect(Money.tryParse('19.99'), const Money(1999));
      expect(Money.tryParse('25'), const Money(2500));
      expect(Money.tryParse('25.5'), const Money(2550));
      expect(Money.tryParse(' 7.05 '), const Money(705));
      expect(Money.tryParse('-3.10'), const Money(-310));
    });

    test('rounds extra decimals to the cent, half up', () {
      expect(Money.tryParse('1.005'), const Money(101));
      expect(Money.tryParse('1.004'), const Money(100));
      expect(Money.tryParse('0.999'), const Money(100));
    });

    test('tolerates JSON numbers by reading their text', () {
      expect(Money.tryParse(25), const Money(2500));
      expect(Money.tryParse(19.99), const Money(1999));
    });

    test('missing or malformed values are null, not zero', () {
      expect(Money.tryParse(null), isNull);
      expect(Money.tryParse(''), isNull);
      expect(Money.tryParse('25,00'), isNull);
      expect(Money.tryParse('veinte'), isNull);
      expect(Money.tryParse('1e3'), isNull);
      expect(Money.tryParse(true), isNull);
    });

    test('writes back the API form', () {
      expect(const Money(2500).toWire(), '25.00');
      expect(const Money(5).toWire(), '0.05');
      expect(const Money(-310).toWire(), '-3.10');
    });

    test('keeps the currency it is given', () {
      expect(Money.tryParse('1.00', currency: 'GBP')!.currency, 'GBP');
      expect(Money.tryParse('1.00'),
          isNot(Money.tryParse('1.00', currency: 'GBP')));
    });
  });

  group('MoneyLabels', () {
    test('formats euros for each app language', () {
      const fee = Money(2500);
      expect(MoneyLabels.forLanguage('es').format(fee), '25,00\u00A0€');
      expect(MoneyLabels.forLanguage('ca').format(fee), '25,00\u00A0€');
      expect(MoneyLabels.forLanguage('en').format(fee), '€25.00');
      expect(MoneyLabels.forLanguage('es').format(const Money(123456)),
          '1.234,56\u00A0€');
      expect(MoneyLabels.forLanguage('es').format(const Money(1999)),
          '19,99\u00A0€');
    });
  });

  group('Earnings', () {
    test('lee la respuesta real del servidor', () {
      final earnings = Earnings.fromJson(earningsServerJson());
      expect(earnings.owedTotal.cents, 3000);
      expect(earnings.paidTotal.cents, 2500);
      expect(earnings.items, hasLength(2));
      expect(earnings.items.first.status, EarningStatus.owed);
      final paid = earnings.items.last;
      expect(paid.status, EarningStatus.paid);
      expect(paid.amount?.cents, 2500);
      expect(
        paid.paidAt?.toUtc(),
        DateTime.utc(2026, 10, 14, 20, 19, 46, 483, 508),
      );
    });

    test('parses the contract example and keeps the server totals', () {
      final earnings = Earnings.fromJson(earningsContractJson());

      expect(earnings.currency, 'EUR');
      // El ejemplo del contrato trae 50.00 adeudados con una sola fila de
      // 25.00: la app muestra el total del servidor, no suma las filas.
      expect(earnings.owedTotal, const Money(5000));
      expect(earnings.paidTotal, const Money(2500));
      expect(earnings.isEmpty, isFalse);

      final item = earnings.items.single;
      expect(item.invitationId, '8d2f0000-0000-4000-8000-000000000001');
      expect(item.activityId, '5a1e0000-0000-4000-8000-000000000001');
      expect(item.activityTitle, 'Concierto de Santa Cecilia');
      expect(item.activityStartsAt, DateTime.utc(2026, 11, 22, 17).toLocal());
      expect(item.activityStartsAt!.isUtc, isFalse);
      expect(item.amount, const Money(2500));
      expect(item.status, EarningStatus.owed);
      expect(item.paidAt, isNull);
    });

    test('reads paid items with their payment date', () {
      final paid = Earnings.fromJson(earningsWithPaidJson()).items.last;

      expect(paid.status, EarningStatus.paid);
      expect(paid.paidAt, DateTime.utc(2026, 3, 5, 10, 30).toLocal());
    });

    test('an empty response has zero totals and no items', () {
      final earnings = Earnings.fromJson(emptyEarningsJson());

      expect(earnings.isEmpty, isTrue);
      expect(earnings.owedTotal, const Money(0));
      expect(earnings.paidTotal, const Money(0));
    });

    test('unknown statuses are not shown as debts', () {
      expect(EarningStatus.fromWire('owed'), EarningStatus.owed);
      expect(EarningStatus.fromWire('paid'), EarningStatus.paid);
      expect(EarningStatus.fromWire('cancelled'), EarningStatus.unknown);
      expect(EarningStatus.fromWire(null), EarningStatus.unknown);
    });

    test('tolerates missing fields without inventing amounts', () {
      final earnings = Earnings.fromJson({
        'items': [
          {'status': 'owed', 'amount': null},
          'not an object',
        ],
      });

      expect(earnings.currency, 'EUR');
      expect(earnings.owedTotal, const Money(0));
      final item = earnings.items.single;
      expect(item.amount, isNull);
      expect(item.activityTitle, '');
      expect(item.activityStartsAt, isNull);
    });
  });

  group('paid activities', () {
    test('reads is_paid and fee_amount from the activity', () {
      final summary = ActivitySummary.fromJson(activityJson(
          id: 'a-1',
          title: 'Concierto',
          startsIn: const Duration(days: 2),
          pay: paidActivityFields));

      expect(summary.isPaid, isTrue);
      expect(summary.feeAmount, const Money(2500));
    });

    test('an unpaid activity has no fee', () {
      final summary = ActivitySummary.fromJson(activityJson(
          id: 'a-1', title: 'Ensayo', startsIn: const Duration(days: 2)));

      expect(summary.isPaid, isFalse);
      expect(summary.feeAmount, isNull);
    });

    test('older responses without the fields are unpaid', () {
      final json = activityJson(
          id: 'a-1', title: 'Ensayo', startsIn: const Duration(days: 2))
        ..remove('is_paid')
        ..remove('fee_amount');

      expect(ActivitySummary.fromJson(json).isPaid, isFalse);
    });

    test('the offline agenda keeps the fee', () {
      final summary = ActivitySummary.fromJson(activityJson(
          id: 'a-1',
          title: 'Concierto',
          startsIn: const Duration(days: 2),
          pay: paidActivityFields));
      final restored = ActivitySummary.fromJson(summary.toJson());

      expect(summary.toJson()['fee_amount'], '25.00');
      expect(restored.isPaid, isTrue);
      expect(restored.feeAmount, const Money(2500));
    });
  });
}
