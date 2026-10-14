import 'dart:io';

import 'package:app_settings/app_settings.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

enum PhotoSource { gallery, camera }

/// Imagen elegida, ya reducida y solo en memoria.
class PickedPhoto {
  const PickedPhoto({required this.bytes, required this.filename});

  final Uint8List bytes;
  final String filename;
}

/// El sistema no deja a la app ver las fotos o usar la cámara.
class PhotoPermissionDenied implements Exception {
  const PhotoPermissionDenied(this.source);

  final PhotoSource source;
}

/// No se pudo abrir el selector (sin cámara, error de la plataforma).
class PhotoPickerUnavailable implements Exception {
  const PhotoPickerUnavailable();
}

abstract interface class PhotoPicker {
  /// `null` si la persona cancela.
  Future<PickedPhoto?> pick(PhotoSource source);

  Future<void> openSettings();
}

/// Selector real con `image_picker`.
///
/// Reduce la imagen en el propio móvil para no rozar el límite de 5 MB del
/// servidor, que sigue siendo quien valida tipo, tamaño y contenido. La copia
/// temporal que deja el plugin se borra en cuanto se lee: la foto es privada
/// y no debe quedar en disco.
class ImagePickerPhotoPicker implements PhotoPicker {
  ImagePickerPhotoPicker({ImagePicker? picker})
      : _picker = picker ?? ImagePicker();

  static const maxDimension = 1600.0;
  static const quality = 85;

  final ImagePicker _picker;

  @override
  Future<PickedPhoto?> pick(PhotoSource source) async {
    final XFile? file;
    try {
      file = await _picker.pickImage(
        source: source == PhotoSource.camera
            ? ImageSource.camera
            : ImageSource.gallery,
        maxWidth: maxDimension,
        maxHeight: maxDimension,
        imageQuality: quality,
        preferredCameraDevice: CameraDevice.front,
        // Sin metadatos completos iOS no pide acceso a toda la fototeca.
        requestFullMetadata: false,
      );
    } on PlatformException catch (error) {
      if (error.code == 'photo_access_denied' ||
          error.code == 'camera_access_denied') {
        throw PhotoPermissionDenied(source);
      }
      throw const PhotoPickerUnavailable();
    }
    if (file == null) return null;
    try {
      return PickedPhoto(bytes: await file.readAsBytes(), filename: file.name);
    } finally {
      await _discard(file.path);
    }
  }

  static Future<void> _discard(String path) async {
    try {
      final copy = File(path);
      if (await copy.exists()) await copy.delete();
    } on FileSystemException {
      // La copia vive en la caché temporal del sistema, que la limpia.
    }
  }

  @override
  Future<void> openSettings() => AppSettings.openAppSettings();
}
