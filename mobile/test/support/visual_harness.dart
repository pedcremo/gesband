import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/core/app_controller.dart';
import 'package:gesband_mobile/core/localization/app_strings.dart';
import 'package:gesband_mobile/core/models/models.dart';
import 'package:gesband_mobile/core/repositories/repositories.dart';
import 'package:gesband_mobile/core/storage/secure_session_store.dart';
import 'package:gesband_mobile/core/theme/brand.dart';
import 'package:gesband_mobile/core/theme/theme_controller.dart';
import 'package:gesband_mobile/core/theme/visual_style.dart';
import 'package:gesband_mobile/features/notifications/notification_service.dart';

import 'earnings_fixtures.dart';
import 'fake_notifications.dart';

// Datos sintéticos con la forma exacta del API (AssociationSerializer,
// ActivitySerializer, MemberSerializer, NotificationSerializer y encuestas).

/// `GET /associations/` de una banda sintética.
Map<String, dynamic> associationJson({
  String id = '3f0c0000-0000-4000-8000-000000000001',
  String name = 'Unió Musical de Prova',
  String primary = '#1B4965',
  String secondary = '#CAE9FF',
  String motto = 'Música per a tot el poble',
  String? visualStyle = 'escenario',
  String? colorMode = 'system',
  String? logoUrl,
}) =>
    {
      'id': id,
      'name': name,
      'slug': 'prova',
      'logo_url': logoUrl,
      'primary_color': primary,
      'secondary_color': secondary,
      'motto': motto,
      if (visualStyle != null) 'visual_style': visualStyle,
      if (colorMode != null) 'color_mode': colorMode,
      'timezone': 'Europe/Madrid',
      'permissions': ['activities.view'],
    };

Association associationFor(VisualStyle style,
        {String primary = '#7A1F2B', String secondary = '#C9A227'}) =>
    Association.fromJson(associationJson(
      visualStyle: style.name,
      primary: primary,
      secondary: secondary,
    ));

/// `GET /activities/` para un músico convocado.
Map<String, dynamic> activityJson({
  required String id,
  required String title,
  required Duration startsIn,
  String response = 'pending',
  bool mandatory = false,
  bool reconfirm = false,
  Map<String, dynamic>? transport,
  Map<String, dynamic> pay = unpaidActivityFields,
}) {
  final starts = DateTime.now().toUtc().add(startsIn);
  return {
    'id': id,
    'association': '3f0c0000-0000-4000-8000-000000000001',
    'kind': 'performance',
    'status': 'published',
    'title': title,
    'description': '',
    'location': 'Auditori Municipal',
    'starts_at': starts.toIso8601String(),
    'ends_at': starts.add(const Duration(hours: 2)).toIso8601String(),
    'meeting_at':
        starts.subtract(const Duration(minutes: 45)).toIso8601String(),
    'response_deadline':
        starts.subtract(const Duration(days: 1)).toIso8601String(),
    'uniform': 'Gala',
    'is_mandatory': mandatory,
    ...pay,
    'version': 1,
    'programme': [
      {'id': 'p-1', 'title': 'El Fallero', 'notes': 'Pasodoble', 'order': 1},
      {'id': 'p-2', 'title': 'Suite Valenciana', 'notes': '', 'order': 2},
    ],
    'invitations': const [],
    'my_invitation': {
      'id': 'invitation-$id',
      'member': 'member-1',
      'member_name': 'Marta Sintètica',
      'response': response,
      'response_note': '',
      'responded_at': null,
      'activity_version': 1,
      'needs_reconfirmation': reconfirm,
      'attendance': null,
    },
    'my_transport': transport,
  };
}

List<Map<String, dynamic>> sampleAgenda() => [
      activityJson(
        id: 'a-1',
        title: 'Concierto de Santa Cecilia',
        startsIn: const Duration(days: 2),
        pay: paidActivityFields,
        transport: {
          'label': 'Autobús 1',
          'kind': 'bus',
          'meeting_point': 'Plaça Major',
          'departure_at': null,
          'driver_name': null,
        },
      ),
      activityJson(
        id: 'a-2',
        title: 'Ensayo general',
        startsIn: const Duration(days: 5),
        response: 'accepted',
      ),
      activityJson(
        id: 'a-3',
        title: 'Pasacalle de fiestas',
        startsIn: const Duration(days: 9),
        mandatory: true,
      ),
      activityJson(
        id: 'a-4',
        title: 'Ensayo de metales',
        startsIn: const Duration(days: 40),
        response: 'declined',
      ),
    ];

class FakeActivities implements ActivitiesRepository {
  FakeActivities({List<Map<String, dynamic>>? agenda, this.cachedAt})
      : agenda = agenda ?? sampleAgenda();

  final List<Map<String, dynamic>> agenda;
  final DateTime? cachedAt;
  final sent = <(String, InvitationResponse, String)>[];

  @override
  Future<AgendaSnapshot> listMine(String associationId) async =>
      AgendaSnapshot(agenda.map(ActivitySummary.fromJson).toList(),
          cachedAt: cachedAt);

  @override
  Future<ActivityDetail> getById(
          String associationId, String activityId) async =>
      ActivityDetail.fromJson(
          agenda.firstWhere((item) => item['id'] == activityId));

  @override
  Future<ActivityDetail> respond(
    String associationId,
    String activityId,
    InvitationResponse response, {
    String note = '',
  }) async {
    sent.add((activityId, response, note));
    final item = agenda.firstWhere((item) => item['id'] == activityId);
    (item['my_invitation'] as Map<String, dynamic>)['response'] = response.name;
    return ActivityDetail.fromJson(item);
  }
}

Map<String, dynamic> pollJson({bool canVote = true}) => {
      'id': 'poll-1',
      'question': '¿Dónde hacemos el viaje de la banda?',
      'description': 'Elige el destino del viaje de primavera.',
      'status': 'open',
      'closes_at':
          DateTime.now().toUtc().add(const Duration(days: 3)).toIso8601String(),
      'published_at': null,
      'cancel_reason': '',
      'choices': [
        {'id': 'opt-a', 'label': 'València'},
        {'id': 'opt-b', 'label': 'Alacant'},
      ],
      'results': canVote
          ? null
          : {
              'kind': 'provisional',
              'votes_cast': 3,
              'options': [
                {'id': 'opt-a', 'label': 'València', 'votes': 2},
                {'id': 'opt-b', 'label': 'Alacant', 'votes': 1},
              ],
            },
      'participation': {'recipients': 4, 'voted': 3},
      'has_voted': !canVote,
      'can_vote': canVote,
    };

class FakePolls implements PollsRepository {
  @override
  Future<List<Poll>> listMine(String associationId) async => [
        Poll.fromJson(pollJson()),
        Poll.fromJson({...pollJson(canVote: false), 'id': 'poll-2'}),
      ];

  @override
  Future<Poll> getById(String associationId, String pollId) async =>
      Poll.fromJson(pollJson());

  @override
  Future<Poll> vote(String associationId, String pollId, String optionId) =>
      throw UnimplementedError();
}

/// `GET /notifications/` tal como lo envía el servidor.
List<Map<String, dynamic>> inboxJson() => [
      {
        'id': 'n-1',
        'title': 'Cambio de horario',
        'body': 'El ensayo general pasa a las 21:30.',
        'deep_link': 'gesband://activities/a-2',
        'activity': 'a-2',
        'poll': null,
        'read_at': null,
        'created_at': '2026-10-07T18:00:00Z',
      },
      {
        'id': 'n-2',
        'title': 'Nueva encuesta',
        'body': 'Vota el destino del viaje.',
        'deep_link': 'gesband://polls/poll-1',
        'activity': null,
        'poll': 'poll-1',
        'read_at': '2026-10-06T09:00:00Z',
        'created_at': '2026-10-06T08:00:00Z',
      },
    ];

class FakeInbox implements InboxRepository {
  final marked = <String>[];

  @override
  Future<List<InboxNotification>> list() async =>
      inboxJson().map(InboxNotification.fromJson).toList();

  @override
  Future<void> markRead(String notificationId) async =>
      marked.add(notificationId);
}

/// `GET /members/me/`.
Map<String, dynamic> memberJson() => {
      'id': 'member-1',
      'external_id': '',
      'first_name': 'Marta',
      'last_name': 'Sintètica Prova',
      'national_id': '',
      'address': '',
      'phone': '600000000',
      'email': 'marta@example.test',
      'kind': 'musician',
      'status': 'active',
      'photo_url': null,
      'instruments': [
        {'id': 'i-2', 'name': 'Saxo alto', 'is_primary': false},
        {'id': 'i-1', 'name': 'Clarinete', 'is_primary': true},
      ],
      'account': 'account-1',
    };

class FakeProfile implements ProfileRepository {
  FakeProfile({
    this.fail = false,
    Map<String, dynamic>? member,
    this.photo,
    this.earnings,
    this.uploadError,
    this.deleteError,
  }) : member = member ?? memberJson();

  bool fail;
  Map<String, dynamic> member;
  Uint8List? photo;

  /// Respuesta de `GET /members/me/earnings`; por defecto, la del contrato.
  /// Con `earningsError`, falla; con `earningsGate`, espera a completarse.
  Map<String, dynamic>? earnings;
  Object? earningsError;
  Completer<void>? earningsGate;
  int earningsCalls = 0;

  final Object? uploadError;
  final Object? deleteError;
  Completer<void>? uploadGate;
  final uploads = <(String, Uint8List, String)>[];
  final deletions = <String>[];

  @override
  Future<MemberProfile> getMine(String associationId) async {
    if (fail) throw const ApiException('No hay una ficha vinculada');
    return MemberProfile.fromJson(member);
  }

  @override
  Future<Uint8List?> loadPhoto(String url) async => photo;

  @override
  Future<MemberProfile> updatePhoto(
    String associationId,
    Uint8List bytes, {
    required String filename,
  }) async {
    uploads.add((associationId, bytes, filename));
    await uploadGate?.future;
    final error = uploadError;
    if (error != null) throw error;
    member = {
      ...member,
      'photo_url':
          'https://gesband.example.test/api/v1/members/${member['id']}/photo/',
    };
    photo = bytes;
    return MemberProfile.fromJson(member);
  }

  @override
  Future<MemberProfile> deletePhoto(String associationId) async {
    deletions.add(associationId);
    final error = deleteError;
    if (error != null) throw error;
    member = {...member, 'photo_url': null};
    photo = null;
    return MemberProfile.fromJson(member);
  }

  @override
  Future<Earnings> getEarnings(String associationId) async {
    earningsCalls++;
    await earningsGate?.future;
    final error = earningsError;
    if (error != null) throw error;
    return Earnings.fromJson(earnings ?? earningsContractJson());
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

class _SignedIn implements AuthRepository {
  @override
  Future<bool> hasSession() async => true;
  @override
  Future<void> login({required String email, required String password}) async {}
  @override
  Future<void> logout() async {}
}

class _Associations implements AssociationsRepository {
  _Associations(this.items);
  final List<Association> items;
  @override
  Future<List<Association>> listMine() async => items;
}

class _NoSession implements SessionStore {
  @override
  Future<SessionTokens?> readTokens() async => null;
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}

/// Controlador de la app con dobles de prueba. Con una sola banda queda
/// activa; con varias, la app espera a que se elija.
Future<AppController> fakeAppController(
  SharedPreferences preferences, {
  required Association association,
  List<Association>? associations,
  FakeActivities? activities,
  FakeInbox? inbox,
  FakeProfile? profile,
}) async {
  final controller = AppController(
    api: ApiClient(
        baseUrl: 'https://gesband.example.test/api/v1',
        sessionStore: _NoSession()),
    auth: _SignedIn(),
    associationsRepository: _Associations(associations ?? [association]),
    activitiesRepository: activities ?? FakeActivities(),
    profileRepository: profile ?? FakeProfile(),
    inboxRepository: inbox ?? FakeInbox(),
    pollsRepository: FakePolls(),
    agendaCache: AgendaCache(preferences),
    notifications: NotificationController(
      gateway: FakePushGateway(),
      registrations: FakeDeviceRepository(),
      deviceStore: MemoryDeviceStateStore(),
      pendingTests: MemoryPendingPushTestStore(),
      appVersion: '0.1.0+1',
    ),
  );
  await controller.login('marta@example.test', 'sintetica');
  return controller;
}

/// Combinaciones de estilo y modo que deben verse correctamente.
const visualMatrix = [
  (VisualStyle.escenario, Brightness.dark),
  (VisualStyle.escenario, Brightness.light),
  (VisualStyle.partitura, Brightness.light),
  (VisualStyle.partitura, Brightness.dark),
  (VisualStyle.festa, Brightness.light),
  (VisualStyle.festa, Brightness.dark),
];

/// Prepara un móvil de 390×844 dp con la marca, el estilo y el modo dados.
Future<({ThemeController theme, LocaleController locale})> pumpThemed(
  WidgetTester tester, {
  required Widget Function() home,
  required Brand brand,
  required Brightness brightness,
  SharedPreferences? preferences,
  double textScale = 1,
  Size size = const Size(390, 844),
  String language = 'es',
  bool settle = true,
}) async {
  tester.view
    ..physicalSize = size * 3
    ..devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final prefs = preferences ?? await SharedPreferences.getInstance();
  await prefs.setString(ThemeController.brandKey, brand.toStoredJson());
  await prefs.setString(ThemeController.colorModeKey,
      brightness == Brightness.dark ? 'dark' : 'light');
  await prefs.setString('app_locale', language);
  final theme = ThemeController(prefs);
  final locale = LocaleController(prefs);
  await tester.pumpWidget(ListenableBuilder(
    listenable: Listenable.merge([theme, locale]),
    builder: (context, _) => MaterialApp(
      locale: locale.locale,
      theme: theme.light,
      darkTheme: theme.dark,
      themeMode: theme.themeMode,
      localizationsDelegates: const [
        AppStrings.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppStrings.supportedLocales,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context)
            .copyWith(textScaler: TextScaler.linear(textScale)),
        child: LocaleScope(
          controller: locale,
          child: ThemeScope(controller: theme, child: child!),
        ),
      ),
      home: home(),
    ),
  ));
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    await tester.pump();
  }
  return (theme: theme, locale: locale);
}

/// Logotipo sintético (PNG de 1×1, negro), como el de una banda monocroma.
final syntheticLogo = Uint8List.fromList(const [
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, //
  0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
  0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00,
  0x0D, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x60, 0x60, 0x60, 0xF8,
  0x0F, 0x00, 0x01, 0x04, 0x01, 0x00, 0x5F, 0xE5, 0xC3, 0x4B, 0x00, 0x00,
  0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
]);
