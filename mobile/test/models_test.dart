import 'package:flutter_test/flutter_test.dart';

import 'package:gesband_mobile/core/models/models.dart';

/// Forma real de `GET /activities/{id}/` para un músico convocado.
Map<String, dynamic> _activityJson({
  Map<String, dynamic>? myInvitation,
  Map<String, dynamic>? myTransport,
  List<Map<String, dynamic>> invitations = const [],
}) =>
    {
      'id': 'activity-1',
      'title': 'Processó',
      'kind': 'performance',
      'status': 'published',
      'starts_at': '2099-10-04T17:00:00Z',
      'ends_at': '2099-10-04T19:00:00Z',
      'meeting_at': '2099-10-04T16:30:00Z',
      'response_deadline': '2099-10-03T20:00:00Z',
      'location': 'Plaça Major',
      'uniform': 'Gala',
      'description': '',
      'is_mandatory': false,
      'programme': [
        {'title': 'Pasodoble', 'notes': 'Primera parte'},
      ],
      'invitations': invitations,
      'my_invitation': myInvitation,
      'my_transport': myTransport,
    };

void main() {
  test('reads the own response and transport from the server fields', () {
    final detail = ActivityDetail.fromJson(_activityJson(
      myInvitation: {
        'id': 'invitation-1',
        'response': 'declined',
        'response_note': 'Viaje',
        'needs_reconfirmation': false,
      },
      myTransport: {
        'label': 'Autobús 1',
        'kind': 'bus',
        'meeting_point': 'Estación',
        'departure_at': '2099-10-04T15:45:00Z',
        'driver_name': null,
      },
    ));

    expect(detail.summary.type, ActivityType.performance);
    expect(detail.summary.place, 'Plaça Major');
    expect(detail.invitationId, 'invitation-1');
    expect(detail.summary.invitationResponse, InvitationResponse.declined);
    expect(detail.responseNote, 'Viaje');
    expect(detail.transport!.label, 'Autobús 1');
    expect(detail.transport!.meetingPoint, 'Estación');
    expect(detail.description, isNull,
        reason: 'una descripción vacía no se muestra');
    expect(detail.canRespond, isTrue);
  });

  test('a board member sees the whole list but has no own invitation', () {
    final detail = ActivityDetail.fromJson(_activityJson(invitations: [
      {'id': 'someone-else', 'response': 'accepted'},
    ]));

    expect(detail.invitationId, isNull);
    expect(detail.summary.invitationResponse, InvitationResponse.pending);
    expect(detail.canRespond, isFalse);
  });

  test('a cancelled answer asks to confirm again', () {
    final summary = ActivitySummary.fromJson(_activityJson(myInvitation: {
      'id': 'invitation-1',
      'response': 'pending',
      'needs_reconfirmation': true,
    }));

    expect(summary.needsReconfirmation, isTrue);
    expect(
        ActivitySummary.fromJson(summary.toJson()).needsReconfirmation, isTrue,
        reason: 'la agenda guardada sin conexión conserva el aviso');
  });

  test('the agenda keeps meeting time, uniform, transport and deadline', () {
    final summary = ActivitySummary.fromJson(_activityJson(
      myInvitation: {'id': 'invitation-1', 'response': 'pending'},
      myTransport: {'label': 'Autobús 1', 'kind': 'bus'},
    ));

    expect(summary.meetingAt, DateTime.parse('2099-10-04T16:30:00Z').toLocal());
    expect(summary.uniform, 'Gala');
    expect(summary.transportLabel, 'Autobús 1');
    expect(summary.hasInvitation, isTrue);
    expect(summary.canRespondAt(DateTime(2099, 10, 1)), isTrue);
    expect(
        summary.canRespondAt(DateTime.parse('2099-10-03T21:00:00Z')), isFalse,
        reason: 'plazo vencido');

    final cached = ActivitySummary.fromJson(summary.toJson());
    expect(cached.meetingAt, summary.meetingAt);
    expect(cached.uniform, 'Gala');
    expect(cached.transportLabel, 'Autobús 1');
    expect(cached.responseDeadline, summary.responseDeadline);
    expect(cached.hasInvitation, isTrue);
  });

  test('without an own invitation the agenda offers no reply', () {
    final summary = ActivitySummary.fromJson(_activityJson());
    expect(summary.hasInvitation, isFalse);
    expect(summary.canRespondAt(DateTime(2099, 10, 1)), isFalse);
  });

  // Regresión: la ficha esperaba `instrument` y el servidor envía la lista
  // `instruments` con el principal marcado.
  test('reads the own profile with the primary instrument', () {
    final profile = MemberProfile.fromJson({
      'id': 'member-1',
      'first_name': 'Marta',
      'last_name': 'Prova',
      'email': '',
      'phone': '600000000',
      'photo_url':
          'https://gesband.example.test/api/v1/members/member-1/photo/',
      'instruments': [
        {'id': 'i-2', 'name': 'Saxo', 'is_primary': false},
        {'id': 'i-1', 'name': 'Clarinete', 'is_primary': true},
      ],
    });

    expect(profile.fullName, 'Marta Prova');
    expect(profile.instrument, 'Clarinete');
    expect(profile.email, isNull);
    expect(profile.photoUrl, endsWith('/photo/'));
  });

  // Regresión: el aviso esperaba `is_read` y `activity_id`; el servidor envía
  // `read_at`, `activity` y `poll`.
  test('reads notices with the server field names', () {
    final unread = InboxNotification.fromJson({
      'id': 'n-1',
      'title': 'Cambio de horario',
      'body': 'El ensayo pasa a las 21:30.',
      'activity': 'a-1',
      'poll': null,
      'read_at': null,
      'created_at': '2026-10-07T18:00:00Z',
    });
    final read = InboxNotification.fromJson({
      'id': 'n-2',
      'title': 'Encuesta',
      'body': '',
      'activity': null,
      'poll': 'p-1',
      'read_at': '2026-10-07T19:00:00Z',
      'created_at': '2026-10-07T18:00:00Z',
    });

    expect(unread.isRead, isFalse);
    expect(unread.activityId, 'a-1');
    expect(read.isRead, isTrue);
    expect(read.pollId, 'p-1');
  });
}
