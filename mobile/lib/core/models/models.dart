enum ActivityType { rehearsal, performance }

enum ActivityStatus { draft, published, cancelled, completed }

enum InvitationResponse { pending, accepted, declined }

class Association {
  const Association({
    required this.id,
    required this.name,
    required this.timeZone,
    this.motto,
    this.logoUrl,
    this.primaryColor,
  });

  factory Association.fromJson(Map<String, dynamic> json) => Association(
        id: json['id'] as String,
        name: json['name'] as String,
        timeZone: json['time_zone'] as String? ??
            json['timezone'] as String? ??
            'Europe/Madrid',
        motto: json['motto'] as String?,
        logoUrl: json['logo_url'] as String?,
        primaryColor: json['primary_color'] as String?,
      );

  final String id;
  final String name;
  final String timeZone;
  final String? motto;
  final String? logoUrl;
  final String? primaryColor;
}

class ProgrammeItem {
  const ProgrammeItem({required this.title, this.notes});

  factory ProgrammeItem.fromJson(Map<String, dynamic> json) => ProgrammeItem(
        title: json['title'] as String,
        notes: json['notes'] as String?,
      );

  final String title;
  final String? notes;
}

class TransportAssignment {
  const TransportAssignment({
    required this.mode,
    this.departurePoint,
    this.departureAt,
    this.driverName,
    this.seatLabel,
  });

  factory TransportAssignment.fromJson(Map<String, dynamic> json) =>
      TransportAssignment(
        mode: json['mode'] as String,
        departurePoint: json['departure_point'] as String?,
        departureAt: json['departure_at'] == null
            ? null
            : DateTime.parse(json['departure_at'] as String).toLocal(),
        driverName: json['driver_name'] as String?,
        seatLabel: json['seat_label'] as String?,
      );

  final String mode;
  final String? departurePoint;
  final DateTime? departureAt;
  final String? driverName;
  final String? seatLabel;
}

class ActivitySummary {
  const ActivitySummary({
    required this.id,
    required this.title,
    required this.type,
    required this.status,
    required this.startsAt,
    required this.invitationResponse,
    required this.isMandatory,
    this.place,
  });

  factory ActivitySummary.fromJson(Map<String, dynamic> json) =>
      ActivitySummary(
        id: json['id'] as String,
        title: json['title'] as String,
        type: ActivityType.values.byName((json['type'] as String?) ??
            (json['kind'] as String?) ??
            'rehearsal'),
        status: ActivityStatus.values.byName(json['status'] as String),
        startsAt: DateTime.parse(json['starts_at'] as String).toLocal(),
        invitationResponse: InvitationResponse.values
            .byName(json['invitation_response'] as String? ?? 'pending'),
        isMandatory: json['is_mandatory'] as bool? ?? false,
        place: json['place'] as String? ?? json['location'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'type': type.name,
        'status': status.name,
        'starts_at': startsAt.toUtc().toIso8601String(),
        'invitation_response': invitationResponse.name,
        'is_mandatory': isMandatory,
        'place': place,
      };

  final String id;
  final String title;
  final ActivityType type;
  final ActivityStatus status;
  final DateTime startsAt;
  final InvitationResponse invitationResponse;
  final bool isMandatory;
  final String? place;
}

class ActivityDetail {
  const ActivityDetail({
    required this.summary,
    required this.programme,
    this.description,
    this.meetingAt,
    this.uniform,
    this.responseDeadline,
    this.transport,
    this.invitationId,
  });

  factory ActivityDetail.fromJson(Map<String, dynamic> json) => ActivityDetail(
        summary: ActivitySummary.fromJson(json),
        description: json['description'] as String?,
        meetingAt: json['meeting_at'] == null
            ? null
            : DateTime.parse(json['meeting_at'] as String).toLocal(),
        uniform: json['uniform'] as String?,
        responseDeadline: json['response_deadline'] == null
            ? null
            : DateTime.parse(json['response_deadline'] as String).toLocal(),
        programme: (json['programme'] as List<dynamic>? ?? const [])
            .map((item) => ProgrammeItem.fromJson(item as Map<String, dynamic>))
            .toList(growable: false),
        transport: json['transport'] == null
            ? null
            : TransportAssignment.fromJson(
                json['transport'] as Map<String, dynamic>,
              ),
        invitationId:
            (json['invitations'] as List<dynamic>?)?.isNotEmpty == true
                ? ((json['invitations'] as List<dynamic>).first
                    as Map<String, dynamic>)['id'] as String?
                : json['invitation_id'] as String?,
      );

  final ActivitySummary summary;
  final String? description;
  final DateTime? meetingAt;
  final String? uniform;
  final DateTime? responseDeadline;
  final List<ProgrammeItem> programme;
  final TransportAssignment? transport;

  final String? invitationId;
}

class MemberProfile {
  const MemberProfile({
    required this.id,
    required this.firstName,
    required this.lastName,
    this.email,
    this.phone,
    this.instrument,
    this.section,
    this.photoUrl,
  });

  factory MemberProfile.fromJson(Map<String, dynamic> json) => MemberProfile(
        id: json['id'] as String,
        firstName: json['first_name'] as String,
        lastName: json['last_name'] as String,
        email: json['email'] as String?,
        phone: json['phone'] as String?,
        instrument: json['instrument'] as String?,
        section: json['section'] as String?,
        photoUrl: json['photo_url'] as String?,
      );

  final String id;
  final String firstName;
  final String lastName;
  final String? email;
  final String? phone;
  final String? instrument;
  final String? section;
  final String? photoUrl;
}

class InboxNotification {
  const InboxNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.isRead,
    this.activityId,
  });

  factory InboxNotification.fromJson(Map<String, dynamic> json) =>
      InboxNotification(
        id: json['id'] as String,
        title: json['title'] as String,
        body: json['body'] as String,
        createdAt: DateTime.parse(json['created_at'] as String).toLocal(),
        isRead: json['is_read'] as bool? ?? false,
        activityId: json['activity_id'] as String?,
      );

  final String id;
  final String title;
  final String body;
  final DateTime createdAt;
  final bool isRead;
  final String? activityId;
}
