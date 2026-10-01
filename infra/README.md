# Infraestructura de Gesband

Esta carpeta contiene un entorno reproducible para desarrollo y ensayo del MVP. No despliega producción ni activa proveedores reales. PostgreSQL y RabbitMQ solo son accesibles desde la red de Compose; Caddy publica el puerto HTTP de desarrollo.

## Inicio local

Requisitos: Docker Engine con el complemento Compose y un backend existente en `backend/` con `requirements.txt` y `manage.py`.

```bash
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/compose.yaml config --quiet
docker compose --env-file infra/.env -f infra/compose.yaml up --build -d
docker compose --env-file infra/.env -f infra/compose.yaml ps
```

El proxy queda en `http://localhost:8080`. Su sonda es `/proxy-health`; Django debe implementar `/health/` sin revelar datos internos. `start-web.sh` aplica migraciones y recopila estáticos antes de iniciar Gunicorn. En despliegues con más de una réplica, las migraciones deberán pasar a una tarea única anterior al arranque.

Los valores de `.env.example` son intencionadamente ficticios. Antes de cualquier entorno compartido hay que cambiar contraseñas y clave de Django, desactivar `DJANGO_DEBUG`, limitar hosts y orígenes, y usar el gestor de secretos del entorno.

## HTTPS

`caddy/Caddyfile.dev` sirve HTTP local. `caddy/Caddyfile.https.example` es la base para un servidor con DNS público: requiere `DOMAIN` y `ACME_EMAIL`, y Caddy debe publicar 80/443 con volúmenes persistentes. Es un ejemplo revisable, no un despliegue automático. No se debe habilitar HSTS hasta confirmar que el dominio funciona exclusivamente por HTTPS.

## Entorno de pruebas en un servidor con otro proxy

Desplegado el 01/10/2026 en `https://gesband.fertion.com`, un VPS Ubuntu 22.04 que ya
servía otras webs con su propio Caddy en 80/443 (`~/ghost_n8n`). Gesband no publica
puertos: su proxy se une a la red del Caddy existente.

1. Requisitos: usuario en el grupo `docker` y Compose v2 (`docker-compose-v2` en
   Ubuntu 22.04; el `docker-compose` 1.x no entiende este `compose.yaml`).
2. `git clone https://github.com/pedcremo/gesband.git ~/gesband` y un `infra/.env`
   propio con secretos generados en el servidor (`secrets.token_urlsafe`), más:
   `COMPOSE_PROJECT_NAME=gesband_test`, `DJANGO_DEBUG=false`,
   `DJANGO_SECURE_COOKIES=true`,
   `DJANGO_ALLOWED_HOSTS=gesband.fertion.com,localhost,127.0.0.1` (las sondas internas
   usan `localhost`), `DJANGO_CSRF_TRUSTED_ORIGINS=https://gesband.fertion.com`,
   `WEB_PORT=127.0.0.1:8088`, `EDGE_NETWORK=ghost_n8n_edge`, `PUSH_PROVIDER=fcm` y
   `FCM_CREDENTIALS_FILE`. La cuenta de servicio va por `scp` a `infra/secrets/`.
3. Arrancar con el fichero adicional:

   ```bash
   docker compose --env-file infra/.env -f infra/compose.yaml -f infra/compose.edge.yaml build web
   docker compose --env-file infra/.env -f infra/compose.yaml -f infra/compose.edge.yaml up -d
   ```

   Se construye primero `web`: si `web` y `worker` construyen a la vez la misma
   imagen, el segundo falla con «already exists».
4. En el Caddy existente, tras copiar su `Caddyfile` y validar el nuevo con
   `caddy validate`, añadir y recargar (`caddy reload`, sin reiniciar):

   ```text
   gesband.fertion.com {
   	encode zstd gzip
   	reverse_proxy gesband-proxy:8080
   }
   ```

   El `Caddyfile` está montado como fichero: hay que escribirlo en el sitio
   (`cat nuevo > Caddyfile`), no sustituirlo, o el contenedor seguirá viendo el viejo.
5. Datos sintéticos: crear la asociación `AUMB` y
   `python manage.py seed_role_accounts --association AUMB --force`.

Actualizar: `git pull` y repetir el paso 3. Comprobación: `curl https://gesband.fertion.com/health/`.

## Copias y restauración

La copia incluye un volcado lógico de PostgreSQL, los archivos privados y sus checksums. RabbitMQ no se copia: los avisos pendientes deben persistir en PostgreSQL y poder reencolarse; la cola no es la fuente de verdad.

```bash
infra/scripts/backup.sh
infra/scripts/verify-backup.sh infra/backups/gesband-FECHA.tar.gz
infra/scripts/restore.sh infra/backups/gesband-FECHA.tar.gz --confirm-replace
```

`backup.sh` exige PostgreSQL en ejecución. `verify-backup.sh` comprueba checksums, que el archivo de medios se puede leer y que `pg_restore` reconoce el volcado. La restauración detiene web, worker y proxy, reemplaza base y medios, reinicia servicios y ejecuta `manage.py check --deploy`.

Antes del piloto se debe ensayar la restauración en un proyecto Compose aislado, verificar una muestra de fichas y fotos sintéticas, y registrar duración y resultado. Las copias reales deberán cifrarse y almacenarse fuera del servidor principal con una política de retención acordada; estos scripts generan el paquete local que alimentará ese proceso.

## Diagnóstico

```bash
docker compose --env-file infra/.env -f infra/compose.yaml ps
docker compose --env-file infra/.env -f infra/compose.yaml logs --tail=200 web worker proxy
docker compose --env-file infra/.env -f infra/compose.yaml exec web python manage.py check
```

Los adaptadores locales usan correo por consola y proveedor push falso. No introduzcas credenciales FCM/APNs o SMTP en `.env.example`, imágenes ni Git.

### Los contenedores pierden internet al cambiar de red

Si el PC cambia de red (otra wifi, compartir conexión del móvil, VPN), los
contenedores que ya estaban en marcha conservan el DNS anterior y dejan de resolver
nombres. El síntoma es `Temporary failure in name resolution` en el worker al enviar
push o correo. Se arregla reiniciándolos:

```bash
docker compose --env-file infra/.env -f infra/compose.yaml restart web worker
```

Un fallo así no deja avisos atascados: el envío se reintenta y, si sigue sin red,
la entrega o la prueba queda como fallida con su código.

