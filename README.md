Quiero hacer una aplicación para gestionar bandas de música de pueblos

Las bandas de música son unas asociaciones muy activas y representativas de la vida cultural de un pueblo. En la comunidad valenciana hay cientos de ellas. 

El número de miembros puede llegar a 300.
Tienen una junta directiva que hace muchas funciones:
- Planificar ensayos 
- Anotar quien va o no va a los ensayos
- Hacer listas para ir a tocar a diferentes actos o pueblos
- Pagar a los músicos según sus actuaciones o si han puesto coche para los desplazamientos
- Cobrar cuotas a los socios para el mantenimiento de la asociación: Los músicos son socios y 
- Contactar con miembros de otras bandas para reforzar salidas
- Notificar para cada acto que vestimenta es la adecuada 

hay otros q no son miembros de la banda pero son como mecenas

La junta tiene un presidente/a, vicepresidencia, contratista, tesorero y vocales

Hay un director musical. Es el q planifica los repertorios a usar y a ensayar y quien dirije
los ensayos.

La intención es hacer una aplicación para móvil android y IOS con una base de código común
La aplicación debe de funcionar bien y con notificaciones. 
Debe poder tambier enviar comunicaciones por whatsapp; tanto a grupos como a individuos

De cada músico miembro de la banda debemos tener sus datos personales. Nombre, apellidos, dni
dirección, teléfono móvil, email, cuerda (musical)

Cada usuario músico podrá saber horario de ensayos. A que actuaciones/salidas está convocado y con que uniforme acudir
Q transporte tiene asignado (opcional). Recibirà notificaciones de esto siempre q las tenga activadas
Además recibirá por correo las mismas.


Quiero q la aplicación sea configurable con el logo y el esquema de color y lemas q escoja cada 
asociación.

Quiero un análisis de software con requerimientos técnicos similares y libre q se pueda aprovechar
como base.

La aplicación guardará todos los datos en la nube. Dispongo de servidores virtuales propios con ubuntu
LA carga inicial en modo bulk de los datos debe de ser sencilla para los administradores de la app
(usualmente miembros de la junta directiva)

La aplicación será gratuita para prueba completamente funcional 6 meses. A los 6 meses caducará
conexión con la nube si no se paga subscripción. La subscripción tendrá diferentes escalas de precios en función de los miembros


De momento esto es todo hasta ver q análisis haces. Q tecnologias escoges y otros parámetros

## Desarrollo del MVP

La propuesta y el alcance ejecutable están documentados en [ANALISIS.md](ANALISIS.md), y las reglas de trabajo en [AGENTS.md](AGENTS.md).

Backend local (requiere Python 3.13 y las dependencias de `backend/requirements.txt`):

```bash
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/python backend/manage.py compilemessages --ignore=.venv
.venv/bin/python backend/manage.py migrate
.venv/bin/python backend/manage.py runserver
```

La API queda en `http://127.0.0.1:8000/api/v1/`, el panel en `http://127.0.0.1:8000/panel/` y la documentación OpenAPI en `/api/docs/`. Para ejecutar la comprobación y las pruebas:

```bash
.venv/bin/python backend/manage.py check
.venv/bin/python backend/manage.py test backend.tests
```

### Cuentas de prueba por rol

Las credenciales, lo que ve cada rol y los puntos abiertos del piloto están en
[INSTRUCCIONES.md](INSTRUCCIONES.md).

Para observar el producto desde cada situación hay un comando que crea una cuenta
sintética por rol de la asociación, ninguna superusuaria, con su ficha de miembro
vinculada y convocada a las actividades publicadas futuras:

```bash
.venv/bin/python backend/manage.py seed_role_accounts --association AUMB
```

Sobre el entorno Docker:

```bash
docker compose --env-file infra/.env -f infra/compose.yaml exec web \
    python manage.py seed_role_accounts --force
```

Es idempotente: al repetirlo no duplica cuentas, accesos, fichas ni convocatorias.
Las direcciones usan un dominio reservado (`.invalid` por omisión) y el comando
rechaza cualquier otro, de modo que nunca pueden corresponder a personas reales ni
recibir correo. Las fichas creadas llevan `external_id` con el prefijo `DEMO-`.

Opciones útiles: `--password` y `--reset-password` para fijar la contraseña,
`--no-invite` para no tocar las actividades existentes y `--force` para ejecutarlo
con `DEBUG` desactivado. Un superusuario como el creado con `createsuperuser` no
sirve para probar permisos: `require_roles` lo deja pasar siempre y la API le
devuelve `["*"]`.

La interfaz permite elegir castellano, valenciano o inglés. El panel conserva la
preferencia en el navegador y la aplicación móvil en el dispositivo; la API respeta
el encabezado `Accept-Language` enviado por el cliente.

El entorno reproducible de PostgreSQL, RabbitMQ, worker y proxy está en `infra/compose.yaml`. Los ejemplos de configuración no contienen secretos reales.

```bash
cp -n infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/compose.yaml up --build -d
docker compose --env-file infra/.env -f infra/compose.yaml run --rm --no-deps web python manage.py test tests
curl --fail http://localhost:8080/health/
```

El contrato se valida según [contracts/README.md](contracts/README.md). La carga de
YAML por sí sola solo comprueba la sintaxis; el lint semántico indicado allí es la
comprobación del contrato.

Cliente Flutter:

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
flutter analyze --fatal-infos --fatal-warnings
flutter test
```

El SDK estable usado y fijado para CI es Flutter 3.47.5. En este entorno está instalado en `/home/pedcremo/.local/share/flutter`; si una terminal no lo encuentra, ejecuta `export PATH=/home/pedcremo/.local/share/flutter/bin:$PATH`.

La app guía la activación de notificaciones y comprueba permiso, registro y prueba de recepción antes de continuar al uso normal. Para publicar en iOS hay que configurar Firebase/APNs y compilar en macOS con Xcode.
