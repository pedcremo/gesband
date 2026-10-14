import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:gesband_mobile/core/api/api_client.dart';
import 'package:gesband_mobile/core/app_controller.dart';
import 'package:gesband_mobile/core/theme/brand.dart';
import 'package:gesband_mobile/core/theme/visual_style.dart';
import 'package:gesband_mobile/features/profile/photo_picker.dart';
import 'package:gesband_mobile/features/profile/profile_screen.dart';

import 'support/earnings_fixtures.dart';
import 'support/finders.dart';
import 'support/visual_harness.dart';

class FakePhotoPicker implements PhotoPicker {
  FakePhotoPicker({this.result, this.error});

  PickedPhoto? result;
  Object? error;
  final sources = <PhotoSource>[];
  var settingsOpened = 0;

  @override
  Future<PickedPhoto?> pick(PhotoSource source) async {
    sources.add(source);
    final failure = error;
    if (failure != null) throw failure;
    return result;
  }

  @override
  Future<void> openSettings() async => settingsOpened++;
}

final _picked = PickedPhoto(bytes: syntheticLogo, filename: 'scaled_1.jpg');

Map<String, dynamic> _memberWithPhoto() => {
      ...memberJson(),
      'photo_url':
          'https://gesband.example.test/api/v1/members/member-1/photo/',
    };

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  final association = associationFor(VisualStyle.escenario);

  Future<AppController> pumpProfile(
    WidgetTester tester, {
    required FakeProfile profile,
    FakePhotoPicker? picker,
    String language = 'es',
    bool settle = true,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final controller = await fakeAppController(prefs,
        association: association, profile: profile);
    tester.view
      ..physicalSize = const Size(390, 844) * 3
      ..devicePixelRatio = 3;
    await pumpThemed(
      tester,
      home: () => Scaffold(
        body: ProfileScreen(
          controller: controller,
          photoPicker: picker ?? FakePhotoPicker(),
        ),
      ),
      brand: Brand.fromAssociation(association),
      brightness: Brightness.light,
      preferences: prefs,
      language: language,
      settle: settle,
    );
    return controller;
  }

  Future<void> openPhotoSheet(WidgetTester tester) async {
    await tester.tap(find.byKey(const Key('photo-action')));
    await tester.pumpAndSettle();
  }

  group('foto propia', () {
    testWidgets('sin foto se ofrece añadirla desde galería o cámara',
        (tester) async {
      await pumpProfile(tester, profile: FakeProfile());

      expect(find.text('Añadir foto'), findsOneWidget);
      expect(find.textContaining('Tu foto es privada'), findsOneWidget);
      await openPhotoSheet(tester);

      expect(find.byKey(const Key('photo-gallery')), findsOneWidget);
      expect(find.byKey(const Key('photo-camera')), findsOneWidget);
      expect(find.byKey(const Key('photo-delete')), findsNothing);
    });

    testWidgets('se sube desde la galería y se muestra al momento',
        (tester) async {
      final profile = FakeProfile();
      final picker = FakePhotoPicker(result: _picked);
      await pumpProfile(tester, profile: profile, picker: picker);
      expect(
          find.descendant(
              of: find.byKey(const Key('profile-card')),
              matching: find.byType(Image)),
          findsNothing);

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-gallery')));
      await tester.pumpAndSettle();

      expect(picker.sources, [PhotoSource.gallery]);
      final (associationId, bytes, filename) = profile.uploads.single;
      expect(associationId, association.id);
      expect(bytes, syntheticLogo);
      expect(filename, 'scaled_1.jpg');
      expect(find.text('Foto actualizada.'), findsOneWidget);
      expect(find.text('Cambiar foto'), findsOneWidget);
      final image = tester.widget<Image>(find.descendant(
          of: find.byKey(const Key('profile-card')),
          matching: find.byType(Image)));
      expect((image.image as MemoryImage).bytes, syntheticLogo);
    });

    testWidgets('mientras sube se indica y no se puede repetir',
        (tester) async {
      final gate = Completer<void>();
      final semantics = tester.ensureSemantics();
      final profile = FakeProfile()..uploadGate = gate;
      await pumpProfile(tester,
          profile: profile, picker: FakePhotoPicker(result: _picked));

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-camera')));
      await tester.pump();
      await tester.pump();

      expect(find.byKey(const Key('photo-busy')), findsOneWidget);
      expect(
          find.bySemanticsLabel(RegExp('Subiendo la foto…')), findsOneWidget);
      expect(
          tester
              .widget<ButtonStyleButton>(find.byKey(const Key('photo-action')))
              .enabled,
          isFalse);

      gate.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('photo-busy')), findsNothing);
      expect(find.text('Foto actualizada.'), findsOneWidget);
      semantics.dispose();
    });

    testWidgets('un rechazo del servidor muestra su mensaje de validación',
        (tester) async {
      final profile = FakeProfile(
        uploadError: const ApiException('El archivo no es una imagen válida.',
            statusCode: 400, fromServer: true),
      );
      await pumpProfile(tester,
          profile: profile, picker: FakePhotoPicker(result: _picked));

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-gallery')));
      await tester.pumpAndSettle();

      expect(
          find.text(
              'No se pudo subir la foto. El archivo no es una imagen válida.'),
          findsOneWidget);
      expect(find.text('Añadir foto'), findsOneWidget);
    });

    testWidgets('un fallo de red usa el mensaje genérico', (tester) async {
      final profile =
          FakeProfile(uploadError: const ApiException('Error de conexión'));
      await pumpProfile(tester,
          profile: profile, picker: FakePhotoPicker(result: _picked));

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-gallery')));
      await tester.pumpAndSettle();

      expect(find.text('No se pudo subir la foto.'), findsOneWidget);
    });

    testWidgets('si se cancela la selección no se sube nada', (tester) async {
      final profile = FakeProfile();
      await pumpProfile(tester, profile: profile, picker: FakePhotoPicker());

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-gallery')));
      await tester.pumpAndSettle();

      expect(profile.uploads, isEmpty);
      expect(find.byType(SnackBar), findsNothing);
    });

    testWidgets('sin permiso de galería se explica y se ofrecen los ajustes',
        (tester) async {
      final profile = FakeProfile();
      final picker = FakePhotoPicker(
          error: const PhotoPermissionDenied(PhotoSource.gallery));
      await pumpProfile(tester, profile: profile, picker: picker);

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-gallery')));
      await tester.pumpAndSettle();

      expect(find.textContaining('no tiene permiso para ver tus fotos'),
          findsOneWidget);
      expect(profile.uploads, isEmpty);
      await tester.tap(find.widgetWithText(SnackBarAction, 'Ajustes'));
      await tester.pumpAndSettle();
      expect(picker.settingsOpened, 1);
    });

    testWidgets('sin permiso de cámara o sin cámara no se rompe',
        (tester) async {
      final picker = FakePhotoPicker(
          error: const PhotoPermissionDenied(PhotoSource.camera));
      await pumpProfile(tester, profile: FakeProfile(), picker: picker);

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-camera')));
      await tester.pumpAndSettle();
      expect(find.textContaining('no tiene permiso para usar la cámara'),
          findsOneWidget);

      picker.error = const PhotoPickerUnavailable();
      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-camera')));
      await tester.pumpAndSettle();
      expect(find.text('No se pudo abrir la cámara o la galería.'),
          findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('eliminar pide confirmación; cancelar la conserva',
        (tester) async {
      final profile =
          FakeProfile(member: _memberWithPhoto(), photo: syntheticLogo);
      await pumpProfile(tester, profile: profile);
      expect(find.text('Cambiar foto'), findsOneWidget);

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-delete')));
      await tester.pumpAndSettle();
      expect(find.text('¿Eliminar tu foto?'), findsOneWidget);
      await tester.tap(find.byKey(const Key('photo-delete-cancel')));
      await tester.pumpAndSettle();

      expect(profile.deletions, isEmpty);
      expect(find.text('Cambiar foto'), findsOneWidget);
    });

    testWidgets('eliminar con confirmación quita la foto', (tester) async {
      final profile =
          FakeProfile(member: _memberWithPhoto(), photo: syntheticLogo);
      await pumpProfile(tester, profile: profile);
      expect(
          find.descendant(
              of: find.byKey(const Key('profile-card')),
              matching: find.byType(Image)),
          findsOneWidget);

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-delete')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('photo-delete-confirm')));
      await tester.pumpAndSettle();

      expect(profile.deletions, [association.id]);
      expect(find.text('Foto eliminada.'), findsOneWidget);
      expect(find.text('Añadir foto'), findsOneWidget);
      expect(
          find.descendant(
              of: find.byKey(const Key('profile-card')),
              matching: find.byType(Image)),
          findsNothing);
    });

    testWidgets('si eliminar falla la foto sigue', (tester) async {
      final profile = FakeProfile(
          member: _memberWithPhoto(),
          photo: syntheticLogo,
          deleteError: const ApiException('Error de conexión'));
      await pumpProfile(tester, profile: profile);

      await openPhotoSheet(tester);
      await tester.tap(find.byKey(const Key('photo-delete')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('photo-delete-confirm')));
      await tester.pumpAndSettle();

      expect(find.text('No se pudo eliminar la foto.'), findsOneWidget);
      expect(find.text('Cambiar foto'), findsOneWidget);
    });

    testWidgets('al cerrar sesión no quedan imágenes en la caché',
        (tester) async {
      final controller = await pumpProfile(tester,
          profile:
              FakeProfile(member: _memberWithPhoto(), photo: syntheticLogo));
      await tester.runAsync(() async {
        // Decodifica la foto para que entre en la caché de imágenes.
        await precacheImage(MemoryImage(syntheticLogo),
            tester.element(find.byType(ProfileScreen)));
      });
      expect(imageCache.currentSize, greaterThan(0));

      await controller.logout();

      expect(imageCache.currentSize, 0);
      expect(imageCache.liveImageCount, 0);
    });
  });

  // Regresión: «Reintentar» llamaba a setState con una función que devolvía
  // el Future y Flutter lo rechazaba, así que la ficha no se recargaba.
  testWidgets('la ficha que no carga se puede reintentar', (tester) async {
    final profile = FakeProfile(fail: true);
    await pumpProfile(tester, profile: profile);
    expect(find.byKey(const Key('profile-unavailable')), findsOneWidget);

    profile.fail = false;
    await tester.tap(find.descendant(
        of: find.byKey(const Key('profile-unavailable')),
        matching: find.text('Reintentar')));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('profile-card')), findsOneWidget);
  });

  group('lo que se me debe', () {
    Future<void> showEarnings(WidgetTester tester) async {
      await tester.ensureVisible(findTextAnyCase('Lo que se me debe'));
      await tester.pumpAndSettle();
    }

    testWidgets('mientras carga se indica', (tester) async {
      final gate = Completer<void>();
      final profile = FakeProfile()..earningsGate = gate;
      await pumpProfile(tester, profile: profile, settle: false);
      await tester.pump();

      expect(find.byKey(const Key('earnings-loading')), findsOneWidget);
      gate.complete();
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('earnings-loading')), findsNothing);
      expect(find.byKey(const Key('earnings-card')), findsOneWidget);
    });

    testWidgets('sin actividades remuneradas muestra el estado vacío',
        (tester) async {
      await pumpProfile(tester,
          profile: FakeProfile()..earnings = emptyEarningsJson());
      await showEarnings(tester);

      expect(find.byKey(const Key('earnings-empty')), findsOneWidget);
      expect(
          find.text('Todavía no tienes actividades remuneradas con '
              'asistencia registrada.'),
          findsOneWidget);
    });

    testWidgets('un error se puede reintentar', (tester) async {
      final profile = FakeProfile()
        ..earningsError = const ApiException('Error de conexión');
      await pumpProfile(tester, profile: profile);
      await showEarnings(tester);

      expect(find.byKey(const Key('earnings-error')), findsOneWidget);
      expect(find.text('No se pudo cargar lo que se te debe.'), findsOneWidget);
      expect(find.byKey(const Key('profile-card')), findsOneWidget,
          reason: 'el resto de la ficha no depende de los adeudos');

      profile.earningsError = null;
      await tester.tap(find.descendant(
          of: find.byKey(const Key('earnings-error')),
          matching: find.text('Reintentar')));
      await tester.pumpAndSettle();
      expect(profile.earningsCalls, 2);
      expect(find.byKey(const Key('earnings-card')), findsOneWidget);
    });

    testWidgets('muestra los totales del servidor y cada actividad',
        (tester) async {
      await pumpProfile(tester,
          profile: FakeProfile()..earnings = earningsWithPaidJson());
      await showEarnings(tester);

      expect(
          tester
              .widget<Text>(find.descendant(
                  of: find.byKey(const Key('earnings-owed-total')),
                  matching: find.byType(Text)))
              .data,
          '50,00 €');
      expect(find.text('Total pagado: 25,00 €'), findsOneWidget);

      final owed =
          find.byKey(const Key('earning-8d2f0000-0000-4000-8000-000000000001'));
      await tester.ensureVisible(owed);
      expect(
          find.descendant(
              of: owed, matching: find.text('Concierto de Santa Cecilia')),
          findsOneWidget);
      expect(find.descendant(of: owed, matching: find.text('Adeudado')),
          findsOneWidget);
      expect(find.descendant(of: owed, matching: find.text('25,00 €')),
          findsOneWidget);

      final paid =
          find.byKey(const Key('earning-8d2f0000-0000-4000-8000-000000000003'));
      await tester.ensureVisible(paid);
      expect(
          find.descendant(of: paid, matching: find.textContaining('Pagado el')),
          findsOneWidget);
      expect(find.descendant(of: paid, matching: find.textContaining('2026')),
          findsWidgets);
    });

    testWidgets('en inglés el importe sigue el formato del idioma',
        (tester) async {
      await pumpProfile(tester,
          profile: FakeProfile()..earnings = earningsContractJson(),
          language: 'en');
      await tester.ensureVisible(findTextAnyCase('What I am owed'));
      await tester.pumpAndSettle();

      expect(find.text('Total paid: €25.00'), findsOneWidget);
      expect(find.text('Owed'), findsOneWidget);
    });
  });
}
