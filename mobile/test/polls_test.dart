import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/features/polls/poll_detail_screen.dart';

Map<String, dynamic> pollJson({
  bool canVote = true,
  bool? hasVoted = false,
  String status = 'open',
  Map<String, dynamic>? results,
  Duration closesIn = const Duration(days: 2),
}) =>
    {
      'id': 'poll-1',
      'question': '¿Dónde hacemos el viaje?',
      'description': '',
      'status': status,
      'closes_at': DateTime.now().toUtc().add(closesIn).toIso8601String(),
      'cancel_reason': '',
      'choices': [
        {'id': 'opt-a', 'label': 'Valencia'},
        {'id': 'opt-b', 'label': 'Alacant'},
      ],
      'results': results,
      'participation': {'recipients': 4, 'voted': 1},
      'has_voted': hasVoted,
      'can_vote': canVote,
      'recipients': null,
    };

class FakePollsRepository implements PollsRepository {
  FakePollsRepository(this.current);

  Map<String, dynamic> current;
  final votes = <String>[];
  bool alreadyVoted = false;

  @override
  Future<Poll> getById(String associationId, String pollId) async =>
      Poll.fromJson(current);

  @override
  Future<List<Poll>> listMine(String associationId) async =>
      [Poll.fromJson(current)];

  @override
  Future<Poll> vote(
      String associationId, String pollId, String optionId) async {
    if (alreadyVoted) throw const AlreadyVotedException();
    votes.add(optionId);
    current = pollJson(canVote: false, hasVoted: true, results: {
      'kind': 'provisional',
      'votes_cast': 2,
      'options': [
        {'id': 'opt-a', 'label': 'Valencia', 'votes': 1},
        {'id': 'opt-b', 'label': 'Alacant', 'votes': 1},
      ],
    });
    return Poll.fromJson(current);
  }
}

Widget app(PollsRepository repository) => MaterialApp(
      locale: const Locale('es'),
      localizationsDelegates: const [
        AppStrings.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppStrings.supportedLocales,
      home: PollDetailScreen(
        association: const Association(
            id: 'band-1', name: 'Banda', timeZone: 'Europe/Madrid'),
        pollId: 'poll-1',
        repository: repository,
      ),
    );

void main() {
  test('parses a poll without any field for the chosen option', () {
    final poll = Poll.fromJson(pollJson(status: 'published', results: {
      'kind': 'final',
      'votes_cast': 3,
      'options': [
        {'id': 'opt-a', 'label': 'Valencia', 'votes': 2},
        {'id': 'opt-b', 'label': 'Alacant', 'votes': 1},
      ],
    }));

    expect(poll.status, PollStatus.published);
    expect(poll.results!.kind, PollResultKind.finalResult);
    expect(poll.results!.options.first.votes, 2);
    expect(poll.recipients, 4);
    expect(poll.description, isNull);
  });

  test('an open poll past its deadline awaits publication', () {
    final poll = Poll.fromJson(pollJson(closesIn: const Duration(minutes: -1)));
    expect(poll.awaitingPublication(DateTime.now()), isTrue);
  });

  testWidgets('voting asks for confirmation and then only says you voted',
      (tester) async {
    final repository = FakePollsRepository(pollJson());
    await tester.pumpWidget(app(repository));
    await tester.pumpAndSettle();

    final voteButton = find.widgetWithText(FilledButton, 'Votar');
    expect(tester.widget<FilledButton>(voteButton).onPressed, isNull);

    await tester.tap(find.text('Alacant'));
    await tester.pump();
    await tester.tap(voteButton);
    await tester.pumpAndSettle();

    expect(
        find.textContaining('no se puede cambiar ni retirar'), findsOneWidget);
    expect(repository.votes, isEmpty);

    await tester.tap(find.text('Votar ahora'));
    await tester.pumpAndSettle();

    expect(repository.votes, ['opt-b']);
    expect(find.text('Has votado'), findsOneWidget);
    expect(find.text('Recuento provisional'), findsOneWidget);
    expect(find.byType(RadioListTile<String>), findsNothing);
  });

  testWidgets('cancelling the confirmation does not vote', (tester) async {
    final repository = FakePollsRepository(pollJson());
    await tester.pumpWidget(app(repository));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Valencia'));
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, 'Votar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancelar'));
    await tester.pumpAndSettle();

    expect(repository.votes, isEmpty);
  });

  testWidgets('a second vote rejected by the server is explained',
      (tester) async {
    final repository = FakePollsRepository(pollJson())..alreadyVoted = true;
    await tester.pumpWidget(app(repository));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Valencia'));
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, 'Votar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Votar ahora'));
    await tester.pumpAndSettle();

    expect(find.text('Ya habías votado en esta encuesta.'), findsOneWidget);
  });

  testWidgets('after the deadline the member sees it is pending publication',
      (tester) async {
    final repository = FakePollsRepository(
        pollJson(canVote: false, closesIn: const Duration(hours: -1)));
    await tester.pumpWidget(app(repository));
    await tester.pumpAndSettle();

    expect(
        find.text('Votación cerrada, pendiente de publicar'), findsOneWidget);
    expect(find.text('Recuento provisional'), findsNothing);
  });
}
