# Plan de negocio de Gesband

Fecha: 8 de octubre de 2026.

Gesband es una plataforma para la gestión diaria de sociedades musicales y bandas de pueblo: censo, roles, convocatorias, agenda, respuestas, asistencia, avisos push y por correo, encuestas anónimas, identidad visual por asociación y una app móvil común para Android e iOS.

Este plan parte de la documentación y el estado actual del proyecto en `gesband`: README, ANALISIS.md, INSTRUCCIONES.md, manuales de usuario, decisiones técnicas, modelos de dominio y contrato de producto. También incorpora una lectura de mercado actualizada con fuentes externas.

## Resumen ejecutivo

Gesband debe posicionarse como el sistema operativo ligero de una sociedad musical: menos WhatsApp, menos hojas sueltas, menos dependencia de una o dos personas de la junta, y más trazabilidad en ensayos, actuaciones, asistencia y consultas a la banda.

La oportunidad inicial es clara en la Comunitat Valenciana. La FSMCV declara 546 sociedades musicales, 47.000 músicos, 60.000 alumnos y más de 200.000 socios, con presencia en el 95% de los municipios valencianos de más de 500 habitantes ([FSMCV](https://fsmcv.org/federacion-de-sociedades-musicales-de-la-comunidad-valenciana/presentacion/)). En España, la CESM/DIGICONFE habla de más de 1.300 sociedades musicales, más de 110.000 intérpretes, 120.000 estudiantes y una masa social superior al millón de personas ([DIGICONFE](https://digiconfe.es/)).

La recomendación de negocio es vender primero un SaaS B2B para asociaciones, no una app individual para músicos. Quien paga debe ser la banda o sociedad musical, porque el beneficio económico y organizativo se concentra en la junta: menos horas de coordinación, menos errores en convocatorias, mejor control de asistencia y una comunicación más fiable.

La monetización debe entrar por fases. Durante el piloto, Gesband no debe cortar valor demasiado pronto: conviene usar una prueba funcional de 3 a 6 meses para 5-10 bandas cercanas, con acompañamiento fuerte y precio de adopción. Después, el modelo recomendado es una suscripción anual por asociación, escalada por número de miembros activos, con servicios puntuales de puesta en marcha e importación.

La tesis comercial es: una banda mediana de 80-200 miembros puede justificar entre 290 y 690 euros al año si Gesband sustituye caos recurrente por una operativa fiable. El producto no compite solo con software musical; compite sobre todo con WhatsApp, Excel, Google Forms, PDFs, libretas y memoria oral.

## Producto y propuesta de valor

Gesband resuelve un problema muy concreto: las sociedades musicales son entidades culturales con mucha actividad, gestión voluntaria y una combinación peculiar de necesidades musicales, asociativas y logísticas. No son una empresa, no son un colegio, no son una banda profesional pequeña y no son simplemente un grupo de WhatsApp grande.

La propuesta de valor principal es:

- Para la junta: planificar ensayos y actuaciones, convocar por personas, cuerdas o instrumentos, controlar respuestas, pasar lista, consultar a la banda mediante encuestas anónimas y mantener un censo ordenado.
- Para el músico: tener una agenda personal clara, responder si asistirá, ver uniforme, lugar, hora de concentración, repertorio y transporte asignado, y recibir avisos relevantes.
- Para administración: importar miembros desde CSV/XLSX, gestionar invitaciones, separar ficha y cuenta, distinguir músicos, socios colaboradores y colaboradores externos.
- Para dirección musical: preparar ensayos, repertorio y convocatorias por cuerdas o instrumentos.
- Para organización: preparar actuaciones, controlar disponibilidad y comunicar cambios de hora, lugar o cancelaciones.
- Para la plataforma: operar varias asociaciones separando datos, roles, marca visual e idiomas.

El valor diferencial no está en tener una agenda; está en entender la vida real de una banda: respuesta previa distinta de asistencia real, convocatoria por cuerda, anonimato real en votaciones, histórico de cambios, refuerzos externos, socios no músicos, personalización de cada asociación y notificaciones verificadas.

## Estado actual del producto

Según los manuales y el código, Gesband ya tiene una base de MVP bastante vendible para pilotos:

- Backend Django + Django REST Framework, PostgreSQL, Celery/RabbitMQ y despliegue Docker sobre Ubuntu.
- App móvil Flutter con base común para Android e iOS.
- Panel web para junta, administración, organización y dirección musical.
- Multi-asociación con roles por asociación: `member`, `board`, `organizer`, `director`, `admin`, `platform`, `web_editor`.
- Censo de miembros con tipos: músico socio, socio colaborador/mecenas y colaborador musical externo.
- Importación CSV/XLSX con previsualización, detección de lotes y confirmación.
- Actividades de tipo ensayo o actuación, borrador/publicada/cancelada/completada, convocatorias, respuestas, histórico y asistencia.
- Repertorio básico por actividad.
- Encuestas de opción única con voto anónimo real: se separa el registro de participación de la papeleta.
- Notificaciones persistentes, push, correo y pruebas de recepción push.
- Interfaz en castellano, valenciano e inglés.
- Marca por asociación: nombre, logo, colores y lema.

También hay limitaciones que conviene convertir en roadmap comercial, no esconderlas:

- El repertorio no se edita todavía desde el panel después de crear una actividad.
- No hay pantalla de gestión de transporte, aunque el servidor ya contempla transporte.
- No hay recuperación de contraseña de autoservicio.
- No se editan fichas, instrumentos ni fotos desde el panel.
- No se asignan roles de junta desde el panel.
- No hay resumen de confirmaciones/asistencias por cuerda o instrumento.
- No hay gestión de cuotas, recibos, pagos ni liquidaciones.
- WhatsApp sigue siendo manual: no hay integración automática.
- El recorrido completo de push en iOS real sigue siendo una condición antes de lanzamiento público.

## Cliente objetivo y mercado

El cliente inicial ideal es una sociedad musical valenciana de 50 a 250 miembros, con junta activa, calendario frecuente y problemas visibles de comunicación. En especial:

- Bandas con ensayos semanales y muchas actuaciones.
- Bandas que ya sufren saturación de WhatsApp.
- Bandas con junta renovada que quiere ordenar procesos.
- Bandas con músicos jóvenes y veteranos, donde conviven móvil, correo y gestión manual.
- Bandas con necesidad de convocar por cuerdas, instrumentos o formaciones parciales.
- Bandas que necesitan consultar a la masa social sin exponer votos en un grupo.

El mercado valenciano permite una estrategia muy enfocada: 546 sociedades musicales federadas según FSMCV. Si Gesband alcanza un 5% de penetración en ese mercado, serían unas 27 asociaciones. Con un ingreso medio anual de 450-600 euros, eso supone 12.000-16.000 euros anuales recurrentes: suficiente para validar, no suficiente para sostener una empresa completa. Con un 15% de penetración, unas 82 asociaciones, el ARR podría moverse entre 37.000 y 49.000 euros. Para una microempresa o producto especializado, ya empieza a ser defendible.

El mercado nacional amplía el techo: más de 1.300 sociedades musicales representadas por CESM/DIGICONFE. Una penetración del 10% en España, con 130 asociaciones y 550 euros de ingreso medio anual, daría unos 71.500 euros recurrentes al año antes de servicios y complementos.

La lectura realista: Gesband no debe planear como una startup de hipercrecimiento. Debe planear como un SaaS vertical, cercano al cliente, con ventas por confianza, demostraciones, pilotos comarcales y alianzas con federaciones o agrupaciones.

## Problema que resuelve

El problema no es que las bandas no puedan comunicarse; es que se comunican demasiado por canales no estructurados. WhatsApp sirve para avisar, pero no para saber de forma fiable quién ha confirmado, quién falta, qué versión del horario es la buena, qué uniforme toca, quién ha votado sin revelar qué ha votado o qué histórico queda si cambia la actividad.

Dolores principales:

- Convocatorias repartidas entre chats, PDFs, llamadas y hojas de cálculo.
- Dificultad para saber disponibilidad real antes de una actuación.
- Cambios de hora o lugar que no obligan a reconfirmar.
- Asistencia real mezclada con respuesta previa.
- Encuestas en WhatsApp donde el voto no es realmente anónimo.
- Censos incompletos, duplicados o dependientes de una persona.
- Falta de continuidad cuando cambia la junta.
- Notificaciones importantes perdidas entre mensajes informales.
- Problemas de privacidad si fotos, teléfonos o DNIs circulan sin control.

Gesband convierte esos procesos en datos estructurados: actividad, convocatoria, respuesta, asistencia, aviso, entrega, encuesta, participación, papeleta, miembro, rol y asociación.

## Competencia y posicionamiento

Hay cuatro tipos de competencia:

1. Herramientas genéricas gratuitas: WhatsApp, Google Sheets, Google Calendar, Forms, correo y PDFs. Son el rival principal porque ya están adoptadas y no tienen coste directo.
2. Software musical internacional: BandHelper, por ejemplo, combina repertorio, agenda, contactos, finanzas, documentos y apps móviles; sus precios llegan a 200-400 dólares al año para grupos de 21-500 miembros según plan ([BandHelper](https://www.bandhelper.com/main/pricing_upcoming.html)).
3. Nuevas apps específicas de bandas: Trío se presenta en App Store como app para sociedades musicales con ensayos, asistencia, junta, atril, avisos, coche compartido, votaciones, actas, mercenarios y perfil de aficionados ([App Store](https://apps.apple.com/es/app/tr%C3%ADo-gesti%C3%B3n-de-bandas/id6786787848)). Esto confirma demanda y obliga a diferenciarse con ejecución, confianza y foco.
4. Desarrollo a medida o soluciones internas: hojas avanzadas, pequeñas webs, intranets o herramientas hechas por un socio informático.

Posicionamiento recomendado:

Gesband debe ser “la herramienta de gestión de sociedades musicales hecha para la realidad de las bandas valencianas y españolas: junta voluntaria, músicos amateurs, censo asociativo, ensayos, actuaciones, asistencia, avisos fiables y consultas anónimas”.

No conviene competir de inicio como atril digital, biblioteca de partituras o marketplace de músicos. Son funcionalidades atractivas, pero abren frentes complejos: derechos de autor, archivos grandes, usabilidad en ensayo, competencia internacional y soporte alto. Gesband puede llegar ahí más tarde; ahora debe ganar por gestión operativa.

## Modelo de negocio y monetización

### Principio de monetización

Cobrar a la asociación, no al músico. El músico individual no debe sentir que paga por recibir convocatorias de su propia banda. La banda paga por ordenar su gestión.

### Prueba gratuita

La idea original de 6 meses gratis tiene sentido para pilotos acompañados, pero no como prueba pública indefinida. Recomendación:

- Pilotos fundadores: 6 meses gratis o precio simbólico, con compromiso de feedback, reuniones mensuales y permiso para usar testimonio si hay éxito.
- Lanzamiento general: prueba de 60 o 90 días, completamente funcional, sin tarjeta, con caducidad clara.
- Conversión: oferta anual con descuento si contratan antes de acabar la prueba.

Una prueba de 6 meses abierta atrae uso pasivo y retrasa demasiado la validación de pago. En cambio, 6 meses con 5-10 bandas piloto sí es útil porque el calendario musical tiene ciclos: ensayos, actuaciones, fiestas, conciertos y asambleas.

### Planes propuestos

Precios orientativos para validar en entrevistas y pilotos:

| Plan | Para quién | Límite | Precio anual recomendado | Mensual orientativo |
| --- | --- | --- | --- | --- |
| Inicial | Banda pequeña o agrupación en arranque | hasta 60 miembros activos | 190 €/año | 19 €/mes |
| Banda | Sociedad pequeña-media | hasta 150 miembros activos | 390 €/año | 39 €/mes |
| Sociedad | Banda mediana-grande | hasta 300 miembros activos | 690 €/año | 69 €/mes |
| Federación / multi-entidad | Varias bandas o acuerdo comarcal | a medida | desde 1.500 €/año | a medida |

Que debe incluir todo plan:

- App para músicos sin coste individual.
- Panel de junta.
- Censo, importación, invitaciones y roles.
- Actividades, convocatorias, respuestas y asistencia.
- Encuestas anónimas.
- Notificaciones push y correo operativo.
- Marca de la asociación.
- Soporte por correo.

Complementos:

| Complemento | Precio recomendado | Comentario |
| --- | --- | --- |
| Puesta en marcha guiada | 150-300 € una vez | Importación, configuración, formación inicial y primera convocatoria. Muy recomendable para bandas con junta poco técnica. |
| Web pública de la asociación | +190-390 €/año | Activarlo solo cuando el módulo esté maduro; no mezclarlo con el MVP si retrasa ventas. |
| Soporte premium | +25-50 €/mes | Respuesta prioritaria y acompañamiento de campañas concretas. |
| Migración avanzada de datos | presupuesto | Para censos complicados, históricos o datos de terceros. |
| Tesorería/cuotas | futuro módulo Pro | Cobrarlo cuando exista valor real y soporte suficiente. |

### Política de caducidad

Si una asociación no paga, no conviene borrar datos ni cortar de golpe el acceso de los músicos en medio de una actividad. Propuesta:

- 15 días de gracia tras vencimiento.
- Modo solo lectura para junta y músicos después del periodo de gracia.
- Exportación de datos disponible durante al menos 12 meses.
- Reactivación sencilla al renovar.

Esta política genera confianza y evita parecer una herramienta oportunista en un entorno asociativo.

## Estrategia comercial

La venta debe ser relacional y demostrable. Una sociedad musical no comprará por publicidad genérica; comprará si ve que otra banda cercana lo usa y le ahorra trabajo.

### Fase 1: pilotos fundadores

Objetivo: 5-10 bandas en la Comunitat Valenciana.

Criterios:

- Una banda pequeña, una mediana y una grande.
- Al menos una con muchas actuaciones.
- Al menos una con junta técnicamente poco experta.
- Al menos una con varios roles activos: junta, dirección y organización.

Oferta:

- 6 meses gratis o 99 € simbólicos.
- Puesta en marcha incluida.
- Reuniones mensuales de 30 minutos.
- Compromiso de usar: importar censo, crear al menos 10 actividades, publicar encuestas y activar notificaciones.

### Fase 2: conversión y testimonios

Al final del piloto, medir:

- Porcentaje de músicos activados.
- Porcentaje con push verificado.
- Número de actividades publicadas.
- Respuestas por convocatoria.
- Horas ahorradas estimadas por junta.
- Incidencias evitadas o cambios comunicados con éxito.

Con esto preparar casos reales: “La banda X pasó de confirmar por WhatsApp a tener el 82% de respuestas registradas antes del plazo”.

### Fase 3: canal federativo y comarcal

Intentar acuerdos con federaciones o coordinadoras comarcales, pero sin depender de ellos al principio. La ruta más práctica es:

1. Pilotos locales.
2. Testimonios.
3. Demo en reuniones comarcales.
4. Oferta para varias bandas de una comarca.
5. Conversación con federación cuando haya tracción demostrable.

### Mensaje comercial

No vender “digitalización” en abstracto. Vender escenas concretas:

- “Convoca metal y percusión para el ensayo del viernes en dos minutos.”
- “Si cambia la hora de salida, todos reconfirman.”
- “La junta ve quién ha respondido; el músico ve solo lo suyo.”
- “Votaciones anónimas sin depender de WhatsApp.”
- “La siguiente junta hereda orden, no caos.”

## Roadmap de producto orientado a negocio

### Antes de cobrar de forma general

Imprescindible:

- Verificar el flujo push completo en iOS real.
- Recuperación de contraseña.
- Edición de fichas desde panel.
- Edición de instrumentos/cuerdas desde panel.
- Gestión básica de roles desde panel para administradores autorizados.
- Resumen de respuestas y asistencia por cuerda/instrumento.
- Exportaciones básicas CSV.
- Pantalla de transporte en panel.
- Registro de incidencias de entrega de correos/push visible para administración.

### Para aumentar conversión

- Duplicar actividades y ensayos recurrentes simples.
- Plantillas de mensajes para copiar/compartir por WhatsApp sin integración automática.
- App web del músico como respaldo para quien no instale app móvil.
- Mejor onboarding de junta: checklist de “censo importado, primera actividad, primeras invitaciones”.
- Dashboard de adopción por asociación.

### Para subir ARPA

- Web pública de asociación.
- Módulo de cuotas y recibos.
- Liquidaciones por actuación y coche.
- Biblioteca documental controlada.
- Partituras/atril solo si hay demanda clara y se resuelve bien derechos, permisos y almacenamiento.

## Operaciones, costes y soporte

La arquitectura actual permite empezar con coste controlado en servidores Ubuntu propios. Aun así, el coste principal no será infraestructura: será soporte, onboarding y confianza.

Costes esperables por asociación:

- Infraestructura marginal: baja al principio, especialmente compartiendo servidor.
- Correo transaccional: bajo si el volumen es moderado, pero debe elegirse proveedor serio.
- Push: Firebase/APNs no será el coste relevante; la complejidad está en configuración y soporte de dispositivos.
- Almacenamiento: bajo mientras no haya partituras o multimedia pesada.
- Soporte: alto al inicio. Cada banda necesitará ayuda con importación, roles, invitaciones y primeros usos.

Recomendación operativa:

- Cobrar puesta en marcha cuando no sea piloto.
- Mantener una base de conocimiento simple para junta y músicos.
- Preparar vídeos cortos de 2-3 minutos: importar censo, crear actividad, convocar, responder desde app, hacer encuesta.
- Tener un entorno demo con datos ficticios estable.
- No aceptar personalizaciones profundas por banda salvo que encajen en el producto general.

## Proyección económica conservadora

Supuestos:

- Ingreso medio anual por asociación: 450 € en año 1, 550 € en año 2, 620 € en año 3.
- Servicios de puesta en marcha: 150-300 € en parte de las altas.
- Churn anual objetivo: inferior al 10% una vez integrada en la operativa de la banda.
- Canal principal: referencias, demos y pilotos.

| Año | Asociaciones de pago fin de año | ARR aproximado | Servicios/altas | Ingreso total orientativo |
| --- | ---: | ---: | ---: | ---: |
| 1 | 10 | 4.500 € | 2.000-3.000 € | 6.500-7.500 € |
| 2 | 45 | 24.750 € | 8.000-12.000 € | 32.000-37.000 € |
| 3 | 120 | 74.400 € | 20.000-35.000 € | 94.000-109.000 € |

Esta proyección no dibuja una empresa grande, pero sí un SaaS vertical atractivo si el desarrollo se mantiene contenido y el soporte no se desborda. El hito clave no es facturar mucho el primer año; es demostrar que una banda paga, renueva y recomienda.

## Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| La junta vuelve a WhatsApp por costumbre | Alto | Onboarding guiado, primeras actividades acompañadas y recordatorios de uso. |
| Baja activación de músicos | Alto | Invitaciones claras, app sencilla, app web de respaldo y medición de activación. |
| Soporte excesivo | Alto | Cobrar puesta en marcha, vídeos, manuales, limitar personalizaciones. |
| Competidor local avanza rápido | Medio/alto | Diferenciar por fiabilidad, soporte cercano, privacidad, valenciano/castellano y conocimiento del flujo asociativo. |
| Precio percibido como alto | Medio | Plan anual asequible, descuento fundador y demostrar horas ahorradas. |
| Push falla en dispositivos reales | Alto | Completar MUST-NOTIF-01 en Android e iOS antes de vender promesa de avisos fiables. |
| Datos personales sensibles | Alto | Minimizar datos, permisos estrictos, exportación, política de privacidad clara y buenas prácticas RGPD. |
| El módulo de tesorería complica demasiado | Medio | No construirlo hasta validar uso operativo y reglas reales. |
| Dependencia del promotor/desarrollador | Medio | Documentación, backups, despliegue reproducible y procesos de soporte. |

## Métricas clave

Métricas de adopción:

- Asociaciones activas.
- Miembros importados por asociación.
- Miembros invitados y cuentas activadas.
- Dispositivos con push concedido, registrado y prueba recibida.
- Actividades creadas, publicadas y canceladas.
- Tasa de respuesta por convocatoria.
- Tiempo medio hasta primera respuesta.
- Encuestas abiertas, participación y resultados publicados.

Métricas de negocio:

- Conversión de piloto a pago.
- Ingreso medio anual por asociación.
- Churn anual.
- Tiempo de onboarding por asociación.
- Tickets de soporte por asociación/mes.
- Coste de adquisición por canal.
- Referencias generadas por banda.

Métricas de valor:

- Horas ahorradas declaradas por junta.
- Reducción de mensajes manuales para convocatorias.
- Porcentaje de cambios importantes reconfirmados.
- Número de incidencias de “no me enteré” antes y después.

## Plan de acción a 90 días

### Días 1-30: preparar producto vendible para piloto

- Cerrar prueba real de notificaciones en iOS.
- Implementar recuperación de contraseña.
- Mejorar edición de ficha/cuerdas/instrumentos desde panel.
- Crear dashboard mínimo de adopción por asociación.
- Preparar demo con datos ficticios y guion comercial.
- Definir contrato de piloto, privacidad y condiciones de uso.

### Días 31-60: pilotos fundadores

- Seleccionar 5 bandas piloto.
- Importar censos con acompañamiento.
- Hacer una sesión de formación por banda.
- Lograr que cada banda publique al menos 3 actividades y 1 encuesta.
- Medir activación, push y respuestas.
- Recoger objeciones de junta y músicos.

### Días 61-90: conversión y empaquetado comercial

- Corregir los 5 bloqueos más repetidos del piloto.
- Crear página comercial simple: propuesta, capturas, precios y demo.
- Preparar dos casos de éxito.
- Ofrecer conversión anual con descuento fundador.
- Contactar 20 bandas cercanas con demo basada en casos reales.
- Definir si el siguiente módulo de pago será web pública, transporte completo o cuotas.

## Conclusión

Gesband tiene una oportunidad real si mantiene el foco. No necesita ser la plataforma musical total desde el primer año. Debe convertirse primero en la herramienta que una junta abre cada semana para saber qué pasa, quién viene, quién ha respondido y qué se ha comunicado.

La monetización más sana es una suscripción anual por asociación, con prueba controlada, puesta en marcha cobrada y precios ajustados al tamaño de la banda. El producto puede ser atractivo porque ataca un dolor repetido, local, emocional y operativo: cuidar mejor una institución cultural gestionada por personas voluntarias que ya hacen demasiado trabajo invisible.
