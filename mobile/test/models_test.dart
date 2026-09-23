import 'package:flutter_test/flutter_test.dart';

import 'package:gesband_mobile/core/models/models.dart';

void main() {
  test('parses backend activity fields and invitation', () {
    final detail = ActivityDetail.fromJson({
      'id': 'activity-1',
      'title': 'Ensayo general',
      'kind': 'rehearsal',
      'status': 'published',
      'starts_at': '2026-09-21T18:00:00Z',
      'location': 'Casa de la música',
      'invitations': [
        {'id': 'invitation-1', 'response': 'pending'},
      ],
      'programme': [
        {'title': 'Pasodoble', 'notes': 'Primera parte'},
      ],
    });

    expect(detail.summary.type, ActivityType.rehearsal);
    expect(detail.summary.place, 'Casa de la música');
    expect(detail.invitationId, 'invitation-1');
    expect(detail.programme.single.title, 'Pasodoble');
  });
}
