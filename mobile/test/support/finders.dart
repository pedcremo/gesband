import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

/// Texto visible sin distinguir mayúsculas. Escenario pone en mayúsculas los
/// títulos de display (`DisplayText`); la prueba sigue comprobando el mismo
/// contenido sea cual sea el estilo.
Finder findTextAnyCase(String text) => find.byWidgetPredicate(
      (widget) =>
          widget is Text && widget.data?.toLowerCase() == text.toLowerCase(),
      description: 'text "$text" (any case)',
    );
