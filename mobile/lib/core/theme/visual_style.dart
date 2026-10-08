/// Estilos visuales predefinidos que una asociación puede elegir
/// (decisión 0010). `escenario` es el de Gesband por defecto.
enum VisualStyle {
  escenario,
  partitura,
  festa;

  /// Valor de `visual_style` del API. Un valor desconocido o ausente cae a
  /// Escenario, por robustez ante servidores antiguos o futuros.
  static VisualStyle fromWire(Object? value) => switch (value) {
        'partitura' => VisualStyle.partitura,
        'festa' => VisualStyle.festa,
        _ => VisualStyle.escenario,
      };
}

/// Modo de color que fija la asociación (`color_mode`).
enum BandColorMode {
  system,
  light,
  dark;

  /// Un valor desconocido o ausente cae a `system`.
  static BandColorMode fromWire(Object? value) => switch (value) {
        'light' => BandColorMode.light,
        'dark' => BandColorMode.dark,
        _ => BandColorMode.system,
      };
}

/// Elección de la persona en su dispositivo: seguir a la banda o fijar un
/// modo. Se guarda en el dispositivo, no en el servidor.
enum ColorModeChoice {
  band,
  light,
  dark;

  static ColorModeChoice fromStored(String? value) => switch (value) {
        'light' => ColorModeChoice.light,
        'dark' => ColorModeChoice.dark,
        _ => ColorModeChoice.band,
      };
}

/// Modo efectivo: manda la persona si lo ha fijado; si no, la banda.
/// `null` significa seguir al sistema.
bool? resolveDarkMode(BandColorMode band, ColorModeChoice choice) =>
    switch (choice) {
      ColorModeChoice.light => false,
      ColorModeChoice.dark => true,
      ColorModeChoice.band => switch (band) {
          BandColorMode.light => false,
          BandColorMode.dark => true,
          BandColorMode.system => null,
        },
    };
