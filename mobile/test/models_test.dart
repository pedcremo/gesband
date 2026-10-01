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
}
