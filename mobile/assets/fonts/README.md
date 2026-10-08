# Fuentes de la app

Las seis familias del sistema visual (decisión
[0010](../../../docs/decisions/0010-sistema-visual-escenario.md)) van empaquetadas
para que la app funcione sin conexión. Todas son de la
[SIL Open Font License 1.1](licenses/) y no declaran *Reserved Font Name*.

Origen: repositorio oficial [github.com/google/fonts](https://github.com/google/fonts),
rama `main`, commit `5e8a3ba899557829a76cfdac30fa512bda91d7ca` (07/10/2026).

| Familia | Estilo | Fichero de origen | Instancias | Licencia |
| --- | --- | --- | --- | --- |
| Big Shoulders Display | Escenario (display) | `ofl/bigshouldersdisplay/BigShouldersDisplay[wght].ttf` | 800 | `licenses/BigShouldersDisplay-OFL.txt` |
| Instrument Sans | Escenario (texto) | `ofl/instrumentsans/InstrumentSans[wdth,wght].ttf` | 400, 600, 700 (wdth 100) | `licenses/InstrumentSans-OFL.txt` |
| Libre Caslon Text | Partitura (display) | `ofl/librecaslontext/LibreCaslonText[wght].ttf` y `-Italic[wght].ttf` | 400, 700, cursiva 400 | `licenses/LibreCaslonText-OFL.txt` |
| Public Sans | Partitura (texto) | `ofl/publicsans/PublicSans[wght].ttf` | 400, 600, 700 | `licenses/PublicSans-OFL.txt` |
| Bricolage Grotesque | Festa (display) | `ofl/bricolagegrotesque/BricolageGrotesque[opsz,wdth,wght].ttf` | 800 (opsz 36, wdth 100) | `licenses/BricolageGrotesque-OFL.txt` |
| Figtree | Festa (texto) | `ofl/figtree/Figtree[wght].ttf` | 400, 600, 700 | `licenses/Figtree-OFL.txt` |

El repositorio solo publica fuentes variables. Flutter no aplica `fontWeight` al
eje `wght` de forma fiable en todas las plataformas, así que se generan instancias
estáticas de los pesos usados (≈1 MB en total, frente a ≈1,7 MB de las variables):

```bash
pip install fonttools
python3 -m fontTools.varLib.instancer "BigShouldersDisplay[wght].ttf" wght=800 \
  -o BigShouldersDisplay-ExtraBold.ttf --update-name-table
# Igual para el resto: wght=400/600/700 y, donde existen, wdth=100 y opsz=36.
```

Un peso nuevo exige generar su instancia, declararla en `pubspec.yaml` y
mantener aquí la tabla. Las licencias se muestran también en la app, en
*Mi ficha → Licencias*.
