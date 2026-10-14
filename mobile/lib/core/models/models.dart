import '../theme/visual_style.dart';

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
    this.secondaryColor,
    this.visualStyle = VisualStyle.escenario,
    this.colorMode = BandColorMode.system,
  });

  factory Association.fromJson(Map<String, dynamic> json) {
    final motto = (json['motto'] as String?)?.trim();
    return Association(
      id: json['id'] as String,
      name: json['name'] as String,
      timeZone: json['time_zone'] as String? ??
          json['timezone'] as String? ??
          'Europe/Madrid',
      motto: motto == null || motto.isEmpty ? null : motto,
      logoUrl: json['logo_url'] as String?,
      primaryColor: json['primary_color'] as String?,
      secondaryColor: json['secondary_color'] as String?,
      visualStyle: VisualStyle.fromWire(json['visual_style']),
      colorMode: BandColorMode.fromWire(json['color_mode']),
    );
  }

  final String id;
  final String name;
  final String timeZone;

  /// Lema; nulo si la asociación no tiene (el API envía `""`).
  final String? motto;
  final String? logoUrl;
  final String? primaryColor;
  final String? secondaryColor;
  final VisualStyle visualStyle;
  final BandColorMode colorMode;
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

DateTime? _localDate(Object? value) =>
    value is String ? DateTime.parse(value).toLocal() : null;

/// Texto opcional; las cadenas vacías del API cuentan como ausentes.
String? _text(Object? value) {
  if (value is! String) return null;
  final trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

/// Convocatoria propia (`my_invitation`), o los campos planos de la agenda
/// guardada sin conexion.
Map<String, dynamic> _ownInvitation(Map<String, dynamic> json) =>
    (json['my_invitation'] as Map<String, dynamic>?) ?? const {};

/// Transporte asignado a quien consulta (`my_transport`).
class TransportAssignment {
  const TransportAssignment({
    required this.label,
    this.kind,
    this.meetingPoint,
    this.departureAt,
    this.driverName,
  });

  factory TransportAssignment.fromJson(Map<String, dynamic> json) =>
      TransportAssignment(
        label: json['label'] as String? ?? '',
        kind: json['kind'] as String?,
        meetingPoint: (json['meeting_point'] as String?)?.trim().isEmpty == true
            ? null
            : json['meeting_point'] as String?,
        departureAt: _localDate(json['departure_at']),
        driverName: json['driver_name'] as String?,
      );

  final String label;
  final String? kind;
  final String? meetingPoint;
  final DateTime? departureAt;
  final String? driverName;
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
    this.needsReconfirmation = false,
    this.place,
    this.meetingAt,
    this.uniform,
    this.transportLabel,
    this.responseDeadline,
    this.hasInvitation = false,
    this.isPaid = false,
    this.feeAmount,
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
        invitationResponse: InvitationResponse.values.byName(
            _ownInvitation(json)['response'] as String? ??
                json['invitation_response'] as String? ??
                'pending'),
        needsReconfirmation:
            _ownInvitation(json)['needs_reconfirmation'] as bool? ??
                json['needs_reconfirmation'] as bool? ??
                false,
        isMandatory: json['is_mandatory'] as bool? ?? false,
        place: _text(json['place'] ?? json['location']),
        meetingAt: _localDate(json['meeting_at']),
        uniform: _text(json['uniform']),
        transportLabel: _text(
            (json['my_transport'] as Map<String, dynamic>?)?['label'] ??
                json['transport_label']),
        responseDeadline: _localDate(json['response_deadline']),
        hasInvitation:
            json['my_invitation'] != null || json['has_invitation'] == true,
        isPaid: json['is_paid'] as bool? ?? false,
        feeAmount: Money.tryParse(json['fee_amount']),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'type': type.name,
        'status': status.name,
        'starts_at': startsAt.toUtc().toIso8601String(),
        'invitation_response': invitationResponse.name,
        'needs_reconfirmation': needsReconfirmation,
        'is_mandatory': isMandatory,
        'place': place,
        'meeting_at': meetingAt?.toUtc().toIso8601String(),
        'uniform': uniform,
        'transport_label': transportLabel,
        'response_deadline': responseDeadline?.toUtc().toIso8601String(),
        'has_invitation': hasInvitation,
        'is_paid': isPaid,
        'fee_amount': feeAmount?.toWire(),
      };

  final String id;
  final String title;
  final ActivityType type;
  final ActivityStatus status;
  final DateTime startsAt;
  final InvitationResponse invitationResponse;
  final bool needsReconfirmation;
  final bool isMandatory;
  final String? place;
  final DateTime? meetingAt;
  final String? uniform;

  /// Etiqueta del transporte asignado (`my_transport.label`).
  final String? transportLabel;
  final DateTime? responseDeadline;

  /// Hay convocatoria propia (`my_invitation`).
  final bool hasInvitation;

  /// Actividad remunerada (`is_paid`) y su importe (`fee_amount`, en EUR).
  /// Puede ser remunerada sin importe fijado.
  final bool isPaid;
  final Money? feeAmount;

  /// Mismo criterio que [ActivityDetail.canRespond], con los datos de la
  /// agenda: publicada, futura, con convocatoria propia y plazo abierto.
  bool canRespondAt(DateTime now) =>
      hasInvitation &&
      status == ActivityStatus.published &&
      now.isBefore(startsAt) &&
      (responseDeadline == null || !now.isAfter(responseDeadline!));
}

class ActivityDetail {
  const ActivityDetail({
    required this.summary,
    required this.programme,
    this.description,
    this.endsAt,
    this.meetingAt,
    this.uniform,
    this.responseDeadline,
    this.transport,
    this.invitationId,
    this.responseNote,
  });

  factory ActivityDetail.fromJson(Map<String, dynamic> json) {
    final own = _ownInvitation(json);
    final description = json['description'] as String?;
    final uniform = json['uniform'] as String?;
    final note = own['response_note'] as String?;
    return ActivityDetail(
      summary: ActivitySummary.fromJson(json),
      description: description?.trim().isEmpty == true ? null : description,
      endsAt: _localDate(json['ends_at']),
      meetingAt: _localDate(json['meeting_at']),
      uniform: uniform?.trim().isEmpty == true ? null : uniform,
      responseDeadline: _localDate(json['response_deadline']),
      programme: (json['programme'] as List<dynamic>? ?? const [])
          .map((item) => ProgrammeItem.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      transport: json['my_transport'] == null
          ? null
          : TransportAssignment.fromJson(
              json['my_transport'] as Map<String, dynamic>),
      invitationId: own['id'] as String?,
      responseNote: note?.trim().isEmpty == true ? null : note,
    );
  }

  final ActivitySummary summary;
  final String? description;
  final DateTime? endsAt;
  final DateTime? meetingAt;
  final String? uniform;
  final DateTime? responseDeadline;
  final List<ProgrammeItem> programme;
  final TransportAssignment? transport;

  /// Convocatoria propia; nula si quien consulta no esta convocado.
  final String? invitationId;
  final String? responseNote;

  bool get deadlinePassed =>
      responseDeadline != null && DateTime.now().isAfter(responseDeadline!);

  /// Solo se responde a una actividad publicada, futura y con plazo abierto.
  bool get canRespond =>
      invitationId != null &&
      summary.status == ActivityStatus.published &&
      DateTime.now().isBefore(summary.startsAt) &&
      !deadlinePassed;
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

  /// Forma de `GET /members/me/`: los instrumentos llegan en una lista con
  /// el principal marcado (`is_primary`).
  factory MemberProfile.fromJson(Map<String, dynamic> json) {
    final instruments = (json['instruments'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
    final primary =
        instruments.where((item) => item['is_primary'] == true).firstOrNull ??
            instruments.firstOrNull;
    return MemberProfile(
      id: json['id'] as String,
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      email: _text(json['email']),
      phone: _text(json['phone']),
      instrument: _text(primary?['name'] ?? json['instrument']),
      section: _text(json['section']),
      photoUrl: _text(json['photo_url']),
    );
  }

  String get fullName => '$firstName $lastName'.trim();

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
    this.pollId,
  });

  /// El servidor envía `read_at`, `activity` y `poll`; el contrato,
  /// `activity_id` y `poll_id`. Se aceptan ambas formas.
  factory InboxNotification.fromJson(Map<String, dynamic> json) =>
      InboxNotification(
        id: json['id'] as String,
        title: json['title'] as String? ?? '',
        body: json['body'] as String? ?? '',
        createdAt: DateTime.parse(json['created_at'] as String).toLocal(),
        isRead: json['read_at'] != null || json['is_read'] == true,
        activityId: (json['activity'] ?? json['activity_id']) as String?,
        pollId: (json['poll'] ?? json['poll_id']) as String?,
      );

  final String id;
  final String title;
  final String body;
  final DateTime createdAt;
  final bool isRead;
  final String? activityId;
  final String? pollId;
}

enum PollStatus { draft, open, published, cancelled }

enum PollResultKind { provisional, finalResult }

class PollChoice {
  const PollChoice({required this.id, required this.label});

  factory PollChoice.fromJson(Map<String, dynamic> json) => PollChoice(
        id: json['id'] as String,
        label: json['label'] as String,
      );

  final String id;
  final String label;
}

class PollTallyRow {
  const PollTallyRow(
      {required this.id, required this.label, required this.votes});

  factory PollTallyRow.fromJson(Map<String, dynamic> json) => PollTallyRow(
        id: json['id'] as String,
        label: json['label'] as String,
        votes: json['votes'] as int? ?? 0,
      );

  final String id;
  final String label;
  final int votes;
}

class PollResults {
  const PollResults(
      {required this.kind, required this.votesCast, required this.options});

  factory PollResults.fromJson(Map<String, dynamic> json) => PollResults(
        kind: json['kind'] == 'final'
            ? PollResultKind.finalResult
            : PollResultKind.provisional,
        votesCast: json['votes_cast'] as int? ?? 0,
        options: (json['options'] as List<dynamic>? ?? const [])
            .map((item) => PollTallyRow.fromJson(item as Map<String, dynamic>))
            .toList(growable: false),
      );

  final PollResultKind kind;
  final int votesCast;
  final List<PollTallyRow> options;
}

/// Encuesta tal como la ve la cuenta autenticada.
///
/// No hay ningun campo con la opcion elegida: el servidor no la conoce, porque
/// la papeleta no guarda quien la emitio.
class Poll {
  const Poll({
    required this.id,
    required this.question,
    required this.status,
    required this.closesAt,
    required this.choices,
    required this.recipients,
    required this.voted,
    required this.canVote,
    this.description,
    this.results,
    this.hasVoted,
    this.publishedAt,
    this.cancelReason,
  });

  factory Poll.fromJson(Map<String, dynamic> json) {
    final participation =
        json['participation'] as Map<String, dynamic>? ?? const {};
    final description = json['description'] as String?;
    final cancelReason = json['cancel_reason'] as String?;
    return Poll(
      id: json['id'] as String,
      question: json['question'] as String,
      description:
          description == null || description.isEmpty ? null : description,
      status: PollStatus.values.byName(json['status'] as String),
      closesAt: DateTime.parse(json['closes_at'] as String).toLocal(),
      publishedAt: json['published_at'] == null
          ? null
          : DateTime.parse(json['published_at'] as String).toLocal(),
      cancelReason:
          cancelReason == null || cancelReason.isEmpty ? null : cancelReason,
      choices: (json['choices'] as List<dynamic>? ?? const [])
          .map((item) => PollChoice.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
      results: json['results'] == null
          ? null
          : PollResults.fromJson(json['results'] as Map<String, dynamic>),
      recipients: participation['recipients'] as int? ?? 0,
      voted: participation['voted'] as int? ?? 0,
      hasVoted: json['has_voted'] as bool?,
      canVote: json['can_vote'] as bool? ?? false,
    );
  }

  final String id;
  final String question;
  final String? description;
  final PollStatus status;
  final DateTime closesAt;
  final DateTime? publishedAt;
  final String? cancelReason;
  final List<PollChoice> choices;
  final PollResults? results;
  final int recipients;
  final int voted;
  final bool? hasVoted;
  final bool canVote;

  /// Plazo vencido y resultado todavia sin publicar por la junta.
  bool awaitingPublication(DateTime now) =>
      status == PollStatus.open && !now.isBefore(closesAt);
}

/// Importe exacto en céntimos. El API envía los decimales como cadena
/// (`"25.00"`): nunca se convierten a `double` para operar.
class Money {
  const Money(this.cents, {this.currency = 'EUR'});

  static final _decimal = RegExp(r'^(-)?(\d+)(?:\.(\d+))?$');

  /// Acepta `"25.00"`, `"25"`, `"25.5"` y, por tolerancia, números JSON
  /// (se leen por su texto, sin aritmética en coma flotante). Con más
  /// de dos decimales redondea al céntimo (mitad hacia arriba). Devuelve
  /// `null` si el valor falta o no es un decimal.
  static Money? tryParse(Object? value, {String currency = 'EUR'}) {
    final text = switch (value) {
      String() => value.trim(),
      num() => '$value',
      _ => null,
    };
    if (text == null) return null;
    final match = _decimal.firstMatch(text);
    if (match == null) return null;
    final negative = match.group(1) != null;
    final units = int.parse(match.group(2)!);
    final fraction = match.group(3) ?? '';
    var cents = int.parse(fraction.padRight(2, '0').substring(0, 2));
    if (fraction.length > 2 && fraction.codeUnitAt(2) >= 0x35) cents += 1;
    final total = units * 100 + cents;
    return Money(negative ? -total : total, currency: currency);
  }

  final int cents;
  final String currency;

  /// Forma del API: `"25.00"`.
  String toWire() {
    final sign = cents < 0 ? '-' : '';
    final value = cents.abs();
    return '$sign${value ~/ 100}.${(value % 100).toString().padLeft(2, '0')}';
  }

  @override
  bool operator ==(Object other) =>
      other is Money && other.cents == cents && other.currency == currency;

  @override
  int get hashCode => Object.hash(cents, currency);

  @override
  String toString() => '${toWire()} $currency';
}

enum EarningStatus {
  owed,
  paid,

  /// Valor que esta versión de la app no conoce: no se presenta como deuda.
  unknown;

  static EarningStatus fromWire(Object? value) => switch (value) {
        'owed' => owed,
        'paid' => paid,
        _ => unknown,
      };
}

/// Una actividad remunerada con asistencia registrada.
class EarningItem {
  const EarningItem({
    required this.invitationId,
    required this.activityId,
    required this.activityTitle,
    required this.status,
    this.activityStartsAt,
    this.amount,
    this.paidAt,
  });

  factory EarningItem.fromJson(Map<String, dynamic> json, String currency) {
    final activity = json['activity'] as Map<String, dynamic>? ?? const {};
    return EarningItem(
      invitationId: json['invitation'] as String? ?? '',
      activityId: activity['id'] as String? ?? '',
      activityTitle: activity['title'] as String? ?? '',
      activityStartsAt: _localDate(activity['starts_at']),
      amount: Money.tryParse(json['amount'], currency: currency),
      status: EarningStatus.fromWire(json['status']),
      paidAt: _localDate(json['paid_at']),
    );
  }

  final String invitationId;
  final String activityId;
  final String activityTitle;
  final DateTime? activityStartsAt;
  final Money? amount;
  final EarningStatus status;
  final DateTime? paidAt;
}

/// `GET /members/me/earnings`: lo que la banda debe al músico. Los totales
/// son los del servidor; la app no los recalcula.
class Earnings {
  const Earnings({
    required this.currency,
    required this.owedTotal,
    required this.paidTotal,
    required this.items,
  });

  factory Earnings.fromJson(Map<String, dynamic> json) {
    final currency = _text(json['currency']) ?? 'EUR';
    return Earnings(
      currency: currency,
      owedTotal: Money.tryParse(json['owed_total'], currency: currency) ??
          Money(0, currency: currency),
      paidTotal: Money.tryParse(json['paid_total'], currency: currency) ??
          Money(0, currency: currency),
      items: (json['items'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map((item) => EarningItem.fromJson(item, currency))
          .toList(growable: false),
    );
  }

  final String currency;
  final Money owedTotal;
  final Money paidTotal;
  final List<EarningItem> items;

  bool get isEmpty => items.isEmpty;
}
