# Logotipos

## Gesband

Elegido por el promotor el 14/10/2026 entre cuatro propuestas: la **G de
pentagrama**, cinco líneas curvadas que dibujan la G, en oro `#C9A227` sobre el negro
de Escenario `#0F1012`.

| Archivo | Uso |
| --- | --- |
| `gesband-icon.svg` | Icono con esquinas redondeadas: lanzador antiguo de Android y documentos. |
| `gesband-icon-square.svg` | Cuadrado a sangre, para iOS (el sistema recorta las esquinas), tiendas y la app web del músico (icono *maskable*). |
| `gesband-mark.svg` | Solo la G, sin fondo, para colocarla sobre otros fondos. |

Las versiones nativas se generan a partir de estos SVG:

- Android: `mipmap-*/ic_launcher.png` (48–192 px) y el icono adaptativo
  `mipmap-anydpi-v26/ic_launcher.xml`, con el primer plano y la silueta monocroma
  (iconos temáticos de Android 13) en `drawable/` como vectores. El icono pequeño de
  las notificaciones es `drawable/ic_stat_gesband.xml`.
- iOS: `Assets.xcassets/AppIcon.appiconset`, sin canal alfa.

Para regenerar los PNG (Inkscape e ImageMagick):

```bash
R=mobile/android/app/src/main/res
for d in mdpi:48 hdpi:72 xhdpi:96 xxhdpi:144 xxxhdpi:192; do
  inkscape docs/logos/gesband-icon.svg --export-type=png \
    --export-filename=$R/mipmap-${d%%:*}/ic_launcher.png -w ${d##*:} -h ${d##*:}
done
inkscape docs/logos/gesband-icon-square.svg --export-type=png \
  --export-filename=/tmp/icon1024.png -w 1024 -h 1024
for f in mobile/ios/Runner/Assets.xcassets/AppIcon.appiconset/*.png; do
  s=$(identify -format %w "$f")
  convert /tmp/icon1024.png -resize ${s}x${s} -background '#0F1012' -alpha remove -alpha off "$f"
done
```

## Bandas

`logo-AUMB.png`: Unió Musical de Bocairent, banda piloto. Los logotipos de las
bandas se suben desde el panel («Imagen de la banda»); este archivo es solo de
referencia.
