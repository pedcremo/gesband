import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';

enum AppMessage {
  signInFailed,
  associationsLoadFailed,
  notificationsInitializeFailed,
  notificationsPermissionFailed,
  notificationsStatusFailed,
  notificationTestFailed,
  deviceRegistrationRenewalFailed,
  deviceRegistrationFailed,
  notificationConfirmationFailed,
}

class AppStrings {
  AppStrings(this.locale);

  final Locale locale;

  static AppStrings of(BuildContext context) =>
      Localizations.of<AppStrings>(context, AppStrings)!;

  static const delegate = _AppStringsDelegate();

  static const supportedLocales = [Locale('es'), Locale('ca'), Locale('en')];

  String get _language => locale.languageCode;

  String _pick({required String es, required String ca, required String en}) =>
      switch (_language) {
        'ca' => ca,
        'en' => en,
        _ => es,
      };

  String get appName => 'Gesband';
  String get language => _pick(es: 'Idioma', ca: 'Idioma', en: 'Language');
  String languageName(Locale value) => switch (value.languageCode) {
        'ca' => 'Valencià',
        'en' => 'English',
        _ => 'Español',
      };
  String get email =>
      _pick(es: 'Correo electrónico', ca: 'Correu electrònic', en: 'Email');
  String get password =>
      _pick(es: 'Contraseña', ca: 'Contrasenya', en: 'Password');
  String get signIn => _pick(es: 'Entrar', ca: 'Entrar', en: 'Sign in');
  String get retry =>
      _pick(es: 'Reintentar', ca: 'Torna-ho a provar', en: 'Try again');
  String get associations =>
      _pick(es: 'Elige la banda', ca: 'Tria la banda', en: 'Choose your band');
  String get noAssociations => _pick(
      es: 'No tienes ninguna banda disponible.',
      ca: 'No tens cap banda disponible.',
      en: 'You do not have any available bands.');
  String get continueLabel =>
      _pick(es: 'Continuar', ca: 'Continua', en: 'Continue');
  String get signOut =>
      _pick(es: 'Cerrar sesión', ca: 'Tanca la sessió', en: 'Sign out');
  String get changeAssociation =>
      _pick(es: 'Cambiar de banda', ca: 'Canvia de banda', en: 'Change band');
  String get emptyAgenda => _pick(
      es: 'No tienes próximas actividades.',
      ca: 'No tens activitats pròximes.',
      en: 'You have no upcoming activities.');
  String get genericError => _pick(
      es: 'No se pudieron cargar los datos.',
      ca: 'No s’han pogut carregar les dades.',
      en: 'The information could not be loaded.');
  String get activity =>
      _pick(es: 'Actividad', ca: 'Activitat', en: 'Activity');
  String get uniform => _pick(es: 'Uniforme', ca: 'Uniforme', en: 'Uniform');
  String get transport =>
      _pick(es: 'Transporte', ca: 'Transport', en: 'Transport');
  String get programme =>
      _pick(es: 'Programa', ca: 'Programa', en: 'Programme');
  String get response => _pick(es: 'Respuesta', ca: 'Resposta', en: 'Response');
  String get accept =>
      _pick(es: 'Asistiré', ca: 'Assistiré', en: 'I will attend');
  String get decline =>
      _pick(es: 'No asistiré', ca: 'No assistiré', en: 'I will not attend');
  String get mandatoryActivity => _pick(
      es: 'Asistencia obligatoria',
      ca: 'Assistència obligatòria',
      en: 'Mandatory attendance');
  String get mandatoryActivityExplanation => _pick(
      es: 'Si no puedes asistir, debes indicar el motivo.',
      ca: 'Si no pots assistir, has d’indicar el motiu.',
      en: 'If you cannot attend, you must provide a reason.');
  String offlineAgenda(String when) => _pick(
      es: 'Sin conexión con el servidor. Datos guardados el $when.',
      ca: 'Sense connexió amb el servidor. Dades guardades el $when.',
      en: 'No connection to the server. Data saved on $when.');
  String get startsLabel => _pick(es: 'Inicio', ca: 'Inici', en: 'Starts');
  String get endsLabel => _pick(es: 'Final', ca: 'Final', en: 'Ends');
  String get meetingLabel =>
      _pick(es: 'Concentración', ca: 'Concentració', en: 'Meeting time');
  String get placeLabel => _pick(es: 'Lugar', ca: 'Lloc', en: 'Place');
  String get deadlineLabel => _pick(
      es: 'Responder antes de', ca: 'Respondre abans de', en: 'Reply before');
  String get meetingPointLabel => _pick(
      es: 'Punto de encuentro', ca: 'Punt de trobada', en: 'Meeting point');
  String get departureLabel =>
      _pick(es: 'Salida', ca: 'Eixida', en: 'Departure');
  String get driverLabel =>
      _pick(es: 'Conductor', ca: 'Conductor', en: 'Driver');
  String get yourResponse =>
      _pick(es: 'Tu respuesta', ca: 'La teua resposta', en: 'Your reply');
  String responseName(InvitationResponse value) => switch (value) {
        InvitationResponse.pending =>
          _pick(es: 'Sin responder', ca: 'Sense respondre', en: 'Not replied'),
        InvitationResponse.accepted =>
          _pick(es: 'Asistirás', ca: 'Assistiràs', en: 'You will attend'),
        InvitationResponse.declined => _pick(
            es: 'No asistirás', ca: 'No assistiràs', en: 'You will not attend'),
      };
  String get responseSaved => _pick(
      es: 'Respuesta guardada.', ca: 'Resposta guardada.', en: 'Reply saved.');
  String get responseFailed => _pick(
      es: 'No se pudo guardar la respuesta. Inténtalo de nuevo.',
      ca: 'No s’ha pogut guardar la resposta. Torna-ho a provar.',
      en: 'Your reply could not be saved. Please try again.');
  String get reconfirmNotice => _pick(
      es: 'Ha cambiado la fecha, la hora o el lugar: vuelve a confirmar.',
      ca: 'Ha canviat la data, l’hora o el lloc: torna a confirmar.',
      en: 'The date, time or place has changed: please confirm again.');
  String get deadlinePassedNotice => _pick(
      es: 'El plazo de respuesta ha terminado.',
      ca: 'El termini de resposta ha acabat.',
      en: 'The reply deadline has passed.');
  String get activityCancelledNotice => _pick(
      es: 'Esta actividad se ha cancelado.',
      ca: 'Aquesta activitat s’ha cancel·lat.',
      en: 'This activity has been cancelled.');
  String get activityPastNotice => _pick(
      es: 'Esta actividad ya ha pasado.',
      ca: 'Aquesta activitat ja ha passat.',
      en: 'This activity has already taken place.');
  String get notInvitedNotice => _pick(
      es: 'No estás convocado a esta actividad.',
      ca: 'No estàs convocat a aquesta activitat.',
      en: 'You are not invited to this activity.');
  String get absenceReason => _pick(
      es: 'Motivo de la ausencia',
      ca: 'Motiu de l’absència',
      en: 'Reason for absence');
  String get reasonRequired => _pick(
      es: 'Escribe el motivo antes de continuar.',
      ca: 'Escriu el motiu abans de continuar.',
      en: 'Enter the reason before continuing.');
  String get cancel => _pick(es: 'Cancelar', ca: 'Cancel·la', en: 'Cancel');
  String get submitAbsence => _pick(
      es: 'Comunicar ausencia',
      ca: 'Comunica l’absència',
      en: 'Submit absence');
  String get activateNotifications => _pick(
      es: 'Activa los avisos',
      ca: 'Activa els avisos',
      en: 'Turn on notifications');
  String get notificationExplanation => _pick(
      es: 'Necesitamos las notificaciones para avisarte de ensayos, convocatorias y cambios.',
      ca: 'Necessitem les notificacions per a avisar-te d’assaigs, convocatòries i canvis.',
      en: 'We need notifications to tell you about rehearsals, invitations and changes.');
  String get permission => _pick(es: 'Permiso', ca: 'Permís', en: 'Permission');
  String get registeredDevice => _pick(
      es: 'Dispositivo registrado',
      ca: 'Dispositiu registrat',
      en: 'Device registered');
  String get testReceived =>
      _pick(es: 'Prueba recibida', ca: 'Prova rebuda', en: 'Test received');
  String get yes => _pick(es: 'sí', ca: 'sí', en: 'yes');
  String get no => _pick(es: 'no', ca: 'no', en: 'no');
  String get pending => _pick(es: 'pendiente', ca: 'pendent', en: 'pending');
  String get activateNotificationsButton => _pick(
      es: 'Activar notificaciones',
      ca: 'Activa les notificacions',
      en: 'Turn on notifications');
  String get openSystemSettings => _pick(
      es: 'Abrir ajustes del sistema',
      ca: 'Obri els ajustos del sistema',
      en: 'Open system settings');
  String get sendTestNotification => _pick(
      es: 'Enviar aviso de prueba',
      ca: 'Envia un avís de prova',
      en: 'Send test notification');
  String get newNotification => _pick(
      es: 'Tienes un nuevo aviso.',
      ca: 'Tens un avís nou.',
      en: 'You have a new notification.');
  String get open => _pick(es: 'Abrir', ca: 'Obri', en: 'Open');
  String get receiptConfirmed => _pick(
      es: 'Recepción comprobada',
      ca: 'Recepció comprovada',
      en: 'Delivery verified');
  String lastReceiptAt(String when) => _pick(
      es: 'Última recepción comprobada: $when',
      ca: 'Última recepció comprovada: $when',
      en: 'Last verified delivery: $when');
  String get notificationsUnavailable => _pick(
      es: 'Las notificaciones no están disponibles en esta instalación. '
          'Puedes seguir usando la app; los avisos llegarán por correo.',
      ca: 'Les notificacions no estan disponibles en esta instal·lació. '
          'Pots continuar usant l’aplicació; els avisos arribaran per correu.',
      en: 'Notifications are not available on this installation. '
          'You can keep using the app; notices will arrive by email.');
  String get notificationsDeniedExplanation => _pick(
      es: 'Sin permiso no te llegarán los cambios de horario ni las '
          'cancelaciones. El sistema ya no vuelve a preguntar: actívalo en los '
          'ajustes y vuelve a la app.',
      ca: 'Sense permís no t’arribaran els canvis d’horari ni les '
          'cancel·lacions. El sistema ja no torna a preguntar: activa’l als '
          'ajustos i torna a l’aplicació.',
      en: 'Without permission you will not get schedule changes or '
          'cancellations. The system will not ask again: turn it on in '
          'settings and come back to the app.');
  String get notificationsProvisionalExplanation => _pick(
      es: 'Los avisos llegan en silencio, sin sonido ni banner. Para verlos '
          'a tiempo, actívalos del todo en los ajustes.',
      ca: 'Els avisos arriben en silenci, sense so ni bàner. Per a veure’ls '
          'a temps, activa’ls del tot als ajustos.',
      en: 'Notifications arrive silently, without sound or banner. To see '
          'them in time, fully enable them in settings.');
  String get notificationsRegisterExplanation => _pick(
      es: 'El permiso está concedido, pero este dispositivo todavía no está '
          'registrado para recibir avisos.',
      ca: 'El permís està concedit, però este dispositiu encara no està '
          'registrat per a rebre avisos.',
      en: 'Permission is granted, but this device is not registered to '
          'receive notifications yet.');
  String get notificationsTestExplanation => _pick(
      es: 'Envía un aviso de prueba para comprobar que llega a este móvil.',
      ca: 'Envia un avís de prova per a comprovar que arriba a este mòbil.',
      en: 'Send a test notification to check that it reaches this phone.');
  String get notificationsAllSet => _pick(
      es: 'Los avisos están activados y se ha comprobado que llegan.',
      ca: 'Els avisos estan activats i s’ha comprovat que arriben.',
      en: 'Notifications are on and delivery has been verified.');
  String get registerDevice => _pick(
      es: 'Registrar este dispositivo',
      ca: 'Registra este dispositiu',
      en: 'Register this device');
  String get sendBackgroundTest => _pick(
      es: 'Probar con la app en segundo plano',
      ca: 'Prova amb l’aplicació en segon pla',
      en: 'Test with the app in the background');
  String get backgroundTestHint => _pick(
      es: 'Tras enviarla, sal de la app y pulsa el aviso cuando llegue.',
      ca: 'Després d’enviar-la, ix de l’aplicació i polsa l’avís quan arribe.',
      en: 'After sending it, leave the app and tap the notification when it arrives.');
  String get checkTestStatus => _pick(
      es: 'Comprobar la prueba', ca: 'Comprova la prova', en: 'Check the test');
  String get lastTest =>
      _pick(es: 'Última prueba', ca: 'Última prova', en: 'Last test');
  String testStatusName(String wireValue) => switch (wireValue) {
        'queued' => _pick(es: 'en cola', ca: 'en cua', en: 'queued'),
        'provider_accepted' => _pick(
            es: 'enviada, esperando que llegue',
            ca: 'enviada, esperant que arribe',
            en: 'sent, waiting for it to arrive'),
        'provider_failed' => _pick(
            es: 'el servicio de avisos no la aceptó',
            ca: 'el servei d’avisos no l’ha acceptada',
            en: 'the push service rejected it'),
        'received_foreground' => _pick(
            es: 'recibida con la app abierta',
            ca: 'rebuda amb l’aplicació oberta',
            en: 'received with the app open'),
        'opened_from_background' => _pick(
            es: 'abierta desde el aviso',
            ca: 'oberta des de l’avís',
            en: 'opened from the notification'),
        'expired' => _pick(
            es: 'caducada sin confirmar',
            ca: 'caducada sense confirmar',
            en: 'expired without confirmation'),
        _ => _pick(es: 'desconocido', ca: 'desconegut', en: 'unknown'),
      };
  String get notNow => _pick(es: 'Ahora no', ca: 'Ara no', en: 'Not now');
  String get notificationsPendingBanner => _pick(
      es: 'Los avisos no están completamente activados en este móvil.',
      ca: 'Els avisos no estan activats del tot en este mòbil.',
      en: 'Notifications are not fully enabled on this phone.');
  String get review => _pick(es: 'Revisar', ca: 'Revisa', en: 'Review');
  String get notificationsDisabledDetected => _pick(
      es: 'Se han desactivado las notificaciones de Gesband. Reactívalas para '
          'no perderte cambios ni cancelaciones.',
      ca: 'S’han desactivat les notificacions de Gesband. Reactiva-les per a '
          'no perdre’t canvis ni cancel·lacions.',
      en: 'Gesband notifications have been turned off. Turn them back on so '
          'you do not miss changes or cancellations.');
  String get testNotificationReceived => _pick(
      es: 'Aviso de prueba recibido.',
      ca: 'Avís de prova rebut.',
      en: 'Test notification received.');

  // Encuestas
  String get polls => _pick(es: 'Encuestas', ca: 'Enquestes', en: 'Polls');
  String get poll => _pick(es: 'Encuesta', ca: 'Enquesta', en: 'Poll');
  String get emptyPolls => _pick(
      es: 'No tienes encuestas.',
      ca: 'No tens enquestes.',
      en: 'You have no polls.');
  String get pollToVote => _pick(
      es: 'Pendiente de votar', ca: 'Pendent de votar', en: 'Not voted yet');
  String get pollVoted =>
      _pick(es: 'Has votado', ca: 'Has votat', en: 'You have voted');
  String get pollAwaitingPublication => _pick(
      es: 'Votación cerrada, pendiente de publicar',
      ca: 'Votació tancada, pendent de publicar',
      en: 'Voting closed, results pending');
  String get pollPublished => _pick(
      es: 'Resultado publicado',
      ca: 'Resultat publicat',
      en: 'Results published');
  String get pollCancelled => _pick(
      es: 'Encuesta anulada', ca: 'Enquesta anul·lada', en: 'Poll cancelled');
  String get pollOpen =>
      _pick(es: 'Votación abierta', ca: 'Votació oberta', en: 'Voting open');
  String pollClosesAt(String when) => _pick(
      es: 'Se puede votar hasta $when',
      ca: 'Es pot votar fins a $when',
      en: 'Voting closes $when');
  String get pollVote => _pick(es: 'Votar', ca: 'Vota', en: 'Vote');
  String get pollChooseOption => _pick(
      es: 'Elige una opción para votar.',
      ca: 'Tria una opció per a votar.',
      en: 'Choose an option to vote.');
  String get pollConfirmTitle => _pick(
      es: '¿Confirmas tu voto?',
      ca: 'Confirmes el teu vot?',
      en: 'Confirm your vote?');
  String pollConfirmBody(String option) => _pick(
      es: 'Vas a votar «$option». El voto es anónimo: una vez emitido nadie, '
          'ni tú, puede saber qué elegiste, y por eso no se puede cambiar ni retirar.',
      ca: 'Votaràs «$option». El vot és anònim: una vegada emés ningú, ni tu, '
          'pot saber què vas triar, i per això no es pot canviar ni retirar.',
      en: 'You are voting "$option". The vote is anonymous: once cast nobody, '
          'not even you, can tell what you chose, so it cannot be changed or withdrawn.');
  String get pollConfirm =>
      _pick(es: 'Votar ahora', ca: 'Vota ara', en: 'Vote now');
  String get pollAlreadyVoted => _pick(
      es: 'Ya habías votado en esta encuesta.',
      ca: 'Ja havies votat en aquesta enquesta.',
      en: 'You had already voted in this poll.');
  String get pollVoteFailed => _pick(
      es: 'No se pudo registrar el voto.',
      ca: 'No s’ha pogut registrar el vot.',
      en: 'The vote could not be recorded.');
  String get pollProvisional => _pick(
      es: 'Recuento provisional',
      ca: 'Recompte provisional',
      en: 'Provisional count');
  String get pollFinal => _pick(es: 'Resultado', ca: 'Resultat', en: 'Results');
  String pollVotesCast(int cast, int recipients) => _pick(
      es: '$cast votos de $recipients personas consultadas',
      ca: '$cast vots de $recipients persones consultades',
      en: '$cast votes from $recipients people asked');
  String pollOptionVotes(int votes, int percent) => _pick(
      es: '$votes · $percent %',
      ca: '$votes · $percent %',
      en: '$votes · $percent%');
  String get pollAnonymousNote => _pick(
      es: 'Voto anónimo: la aplicación no guarda qué has elegido.',
      ca: 'Vot anònim: l’aplicació no guarda què has triat.',
      en: 'Anonymous vote: the app does not keep what you chose.');
  String get reason => _pick(es: 'Motivo', ca: 'Motiu', en: 'Reason');

  String permissionName(String name) => switch (name) {
        'notDetermined' => _pick(
            es: 'sin solicitar', ca: 'sense sol·licitar', en: 'not requested'),
        'denied' => _pick(es: 'denegado', ca: 'denegat', en: 'denied'),
        'restricted' =>
          _pick(es: 'restringido', ca: 'restringit', en: 'restricted'),
        'provisional' => _pick(
            es: 'provisional (avisos silenciosos)',
            ca: 'provisional (avisos silenciosos)',
            en: 'provisional (quiet notifications)'),
        'granted' => _pick(es: 'concedido', ca: 'concedit', en: 'granted'),
        _ => _pick(es: 'desconocido', ca: 'desconegut', en: 'unknown'),
      };

  String message(AppMessage message) => switch (message) {
        AppMessage.signInFailed => _pick(
            es: 'No se pudo iniciar sesión.',
            ca: 'No s’ha pogut iniciar la sessió.',
            en: 'Could not sign in.'),
        AppMessage.associationsLoadFailed => _pick(
            es: 'No se pudieron cargar tus bandas.',
            ca: 'No s’han pogut carregar les teues bandes.',
            en: 'Your bands could not be loaded.'),
        AppMessage.notificationsInitializeFailed => _pick(
            es: 'No se pudo inicializar el servicio de notificaciones.',
            ca: 'No s’ha pogut iniciar el servei de notificacions.',
            en: 'The notification service could not be started.'),
        AppMessage.notificationsPermissionFailed => _pick(
            es: 'No se pudo solicitar el permiso de notificaciones.',
            ca: 'No s’ha pogut sol·licitar el permís de notificacions.',
            en: 'Notification permission could not be requested.'),
        AppMessage.notificationsStatusFailed => _pick(
            es: 'No se pudo comprobar el estado de las notificaciones.',
            ca: 'No s’ha pogut comprovar l’estat de les notificacions.',
            en: 'Notification status could not be checked.'),
        AppMessage.notificationTestFailed => _pick(
            es: 'No se pudo enviar el aviso de prueba.',
            ca: 'No s’ha pogut enviar l’avís de prova.',
            en: 'The test notification could not be sent.'),
        AppMessage.deviceRegistrationRenewalFailed => _pick(
            es: 'No se pudo renovar el registro del dispositivo.',
            ca: 'No s’ha pogut renovar el registre del dispositiu.',
            en: 'The device registration could not be renewed.'),
        AppMessage.deviceRegistrationFailed => _pick(
            es: 'No se pudo registrar este dispositivo para recibir avisos.',
            ca: 'No s’ha pogut registrar este dispositiu per a rebre avisos.',
            en: 'This device could not be registered for notifications.'),
        AppMessage.notificationConfirmationFailed => _pick(
            es: 'El aviso llegó, pero no se pudo confirmar la prueba.',
            ca: 'L’avís ha arribat, però no s’ha pogut confirmar la prova.',
            en: 'The notification arrived, but the test could not be confirmed.'),
      };
}

class LocaleController extends ChangeNotifier {
  LocaleController(this._preferences)
      : _locale = Locale(_preferences.getString(_preferenceKey) ?? 'es');

  static const _preferenceKey = 'app_locale';
  final SharedPreferences _preferences;
  Locale _locale;

  Locale get locale => _locale;

  Future<void> setLocale(Locale locale) async {
    if (!AppStrings.supportedLocales
        .any((item) => item.languageCode == locale.languageCode)) {
      return;
    }
    if (_locale.languageCode == locale.languageCode) return;
    _locale = Locale(locale.languageCode);
    await _preferences.setString(_preferenceKey, locale.languageCode);
    notifyListeners();
  }
}

class LocaleScope extends InheritedNotifier<LocaleController> {
  const LocaleScope({
    super.key,
    required LocaleController controller,
    required super.child,
  }) : super(notifier: controller);

  static LocaleController of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<LocaleScope>();
    assert(scope != null, 'LocaleScope was not found in the widget tree.');
    return scope!.notifier!;
  }
}

class _AppStringsDelegate extends LocalizationsDelegate<AppStrings> {
  const _AppStringsDelegate();

  @override
  bool isSupported(Locale locale) => AppStrings.supportedLocales
      .any((item) => item.languageCode == locale.languageCode);

  @override
  Future<AppStrings> load(Locale locale) =>
      SynchronousFuture(AppStrings(locale));

  @override
  bool shouldReload(_AppStringsDelegate old) => false;
}
