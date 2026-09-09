# Compatibilidad del Checador con el servidor de staging

**Fecha:** 2026-09-09
**Repo:** `github.com/Capitalcontinental/Checador` (rama `main`)
**Servidor evaluado:** `valexpress-staging` — 45.82.73.42, Hostinger, Ubuntu 26.04.1 LTS,
1 CPU, 3.8 GB RAM, 18 GB libres de 48 GB, Docker 29.7.2, Compose v5.5.0.

---

## Veredicto

**Es compatible, pero el `docker-compose.yml` que hay en el repo NO arranca en ese
servidor.** No es cuestión de ajustar variables: falla al iniciar, y si se le forzara a
arrancar dejaría la API abierta a internet con la contraseña de fábrica.

La causa es una sola y explica los cinco bloqueos: **el compose actual está escrito para la
PC de la oficina** (Docker Desktop, máquina dedicada, WiFi de confianza). El servidor de
staging es una máquina compartida con ValeExpress y expuesta a internet. Son dos entornos
con supuestos opuestos.

La solución no es modificar ese archivo, porque la PC de la oficina lo necesita tal cual.
Se agregó un **`docker-compose.staging.yml`** aparte, siguiendo la misma convención que ya
usa ValeExpress en ese servidor (`docker-compose.staging.yml` + `.env.staging` + bloque de
nginx en el host).

| Dimensión | Estado |
|---|---|
| Versiones (Docker, Compose, Node, Python, Postgres) | Compatible, sin cambios |
| Recursos (CPU, RAM, disco) | Alcanza, con límites puestos |
| Puertos | **3 colisiones**, resueltas |
| Exposición a internet | **Bloqueante**, resuelto |
| Zona horaria | **Bloqueante**, resuelto |
| Persistencia de datos | Frágil, resuelto |
| DNS y TLS | **Falta crear el subdominio** (única tarea manual) |
| Cámara desde el celular | Mejora con HTTPS, no bloquea |

---

## Los 5 bloqueos, con la evidencia que los demuestra

### 1. El puerto 80 no está disponible (arranque falla)

El compose actual pide `"80:80"` para el frontend. En el servidor, nginx del sistema ya
escucha en `0.0.0.0:80` y `0.0.0.0:443`: es quien termina el TLS de
`*.staging.valeexpress.mx`.

Probado en el servidor:

```
$ docker run -d -p 80:80 nginx:alpine
docker: Error response from daemon: failed to set up container networking:
failed to bind host port 0.0.0.0:80/tcp: address already in use
```

No es un aviso, es un fallo de arranque. **Además el 5432 tampoco está libre**
(`valexpress-staging-db` lo tiene tomado en 127.0.0.1).

**Resuelto:** el frontend publica en `127.0.0.1:8085` y el backend en `127.0.0.1:8001`
(ambos verificados libres); Postgres no publica ningún puerto y se alcanza por la red
interna de compose. El nginx del host hace de puerta pública, igual que con los tres
portales de ValeExpress.

### 2. `ports: "8000:8000"` habría puesto la API en internet

Este es el hallazgo más serio, y es contraintuitivo: **ufw no protege los puertos que
publica Docker.** Docker inserta sus reglas DNAT antes de la cadena de ufw, así que
"ufw solo permite 22, 80 y 443" es falso para cualquier contenedor con `-p`.

Medido de verdad, no deducido. En el servidor:

```
$ docker run -d --name prueba_expo_8000 -p 8000:80 nginx:alpine
$ ss -tlnp | grep 8000
LISTEN 0 4096 0.0.0.0:8000 ...
```

Y desde esta laptop, fuera de la red del servidor:

```
$ curl -o /dev/null -w 'HTTP %{http_code}\n' http://45.82.73.42:8000/
HTTP 200
```

Respondió pese a que ufw no tiene regla para el 8000. (El contenedor de prueba se eliminó
al terminar la comprobación.)

Con el compose actual eso significa que habrían quedado accesibles desde cualquier parte
del mundo: `/docs` con el mapa completo de la API, y el login de admin con
`DEFAULT_ADMIN_PASSWORD: ${...:-1234}`, cuatro dígitos que se adivinan al primer intento.

**Resuelto,** con tres candados:

- Todos los puertos atados a `127.0.0.1`. Solo el nginx del host llega, y el nginx del host
  exige HTTPS.
- `DEFAULT_ADMIN_PASSWORD` y `POSTGRES_PASSWORD` sin valor por defecto: usan `:?`, que
  **aborta el arranque** si faltan en vez de sembrar `1234`. Verificado: sin `.env`, el
  compose falla con `required variable POSTGRES_PASSWORD is missing a value`.
- `DOCS_ENABLED=false` apaga `/docs`, `/redoc` y `/openapi.json`. Verificado: los tres
  devuelven **404**.

### 3. El servidor corre en UTC: el reporte de nómina saldría en cero

El servidor está en `Etc/UTC` (`timedatectl`). La oficina está en Mazatlán, MST (-0700).
Es exactamente el bug P0 que documenta `AUDITORIA.md`: una jornada que termina después de
las 17:00 cruza de día en UTC, el reporte la parte en dos filas sin pareja y se contabiliza
como **cero horas trabajadas más una falta falsa**.

El compose de la oficina ya fija `TZ`/`OFFICE_TZ`; el punto es que **en este servidor no es
opcional**, porque el host no lo compensa.

Verificado que la imagen base lo soporta (`python:3.12-slim` trae tzdata):

```
$ docker run --rm python:3.12-slim python -c "from zoneinfo import ZoneInfo; ..."
OK 2026-09-09 15:39:18-07:00
```

Y dentro del contenedor ya levantado:

```
$ docker exec checador_staging_backend date
Wed Sep  9 15:50:21 MST 2026
$ clock.now(): 2026-09-09 15:50:21 | today: 2026-09-09
```

### 4. Los datos vivían en carpetas del repo

El compose actual monta `./data/backups`, `./data/photos` y `./data/punch_photos`, carpetas
dentro del directorio del repo. En la PC de la oficina es cómodo. En el servidor quedarían
bajo `/root`, con permisos de root y fuera de cualquier respaldo. Y como el nombre del
proyecto de compose se deriva del nombre de la carpeta, **mover o renombrar el directorio
crea volúmenes nuevos y el checador arranca con la base vacía** mientras los datos viejos
quedan en un volumen huérfano. Es el mismo problema que ValeExpress ya resolvió con
`name: valexpress-staging` (su BACK-6).

**Resuelto:** `name: checador-staging` fijo, y volúmenes nombrados para respaldos, fotos y
fotos de marcas.

### 5. Sin límites de recursos, un pico del checador tumba ValeExpress

El servidor tiene **1 CPU y 3.8 GB** compartidos con siete contenedores de ValeExpress
(backend 114 MB, Postgres 59 MB, Vector, Redis y tres portales). Hay margen (2.7 GB
disponibles), pero sin límites un crash loop del checador escribiendo logs sin rotación
llena los 18 GB libres y se lleva por delante la app principal.

**Resuelto:** rotación de logs (10 MB x 5 por contenedor) y límites de memoria: backend
768 MB, Postgres 512 MB, frontend 256 MB. Consumo medido en marcha: 108 MB, 28 MB y 15 MB.
Sobra holgura.

---

## Lo que ya era compatible (verificado, no supuesto)

- **Docker 29.7.2 / Compose v5.5.0.** El compose se validó con el binario del propio
  servidor: `docker compose config` → válido.
- **Node 22 y Vite 8.** `vite@8.2.2` exige `node ^20.19 || >=22.12`; `node:22-alpine`
  entrega v22.23.2. El `package-lock.json` existe, así que `npm ci` funciona.
- **Postgres 16-alpine.** Misma imagen que ya corre ahí.
- **`pg_dump` para los respaldos.** Incluido en la imagen del backend (v17.11) y probado
  contra el Postgres del stack: generó un `.sql` de 6.4 KB.
- **Tamaño de imágenes.** 426 MB backend + 104 MB frontend, contra 18 GB libres.

---

## Lo único que falta y requiere una decisión humana

**El subdominio `checador.staging.valeexpress.mx` no existe.** Comprobado: `api.staging`
resuelve a 45.82.73.42, `checador.staging` no resuelve a nada.

Hay que crear el registro A en Cloudflare (zona `valeexpress.mx`) apuntando a
**45.82.73.42**, en modo **DNS only, no proxied**. La razón está escrita en el propio nginx
del servidor: el Universal SSL gratuito de Cloudflare no cubre un tercer nivel como
`*.staging`, por eso ese entorno usa certbot en el host.

No se creó el registro porque toca el DNS de un dominio en producción, y eso lo decide
quien opera la zona. Con el registro creado, el resto son los comandos de la sección
siguiente.

---

## Cómo desplegar

```bash
# 1. En la laptop: copiar el repo al servidor
rsync -az --delete --exclude '.git' --exclude 'node_modules' --exclude 'data' \
  ./ valexpress-staging:/root/checador-staging/

# 2. En el servidor: credenciales (una sola vez)
ssh valexpress-staging
cd /root/checador-staging
cp .env.staging.example .env.staging
openssl rand -base64 24      # una para POSTGRES_PASSWORD
openssl rand -base64 24      # otra para DEFAULT_ADMIN_PASSWORD
nano .env.staging            # pegar ambas

# 3. Levantar
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build

# 4. Comprobar
curl -s http://127.0.0.1:8001/health          # {"status":"ok"}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8001/docs   # 404, correcto
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8085/       # 200

# 5. Puerta pública (tras crear el DNS)
cp deploy/nginx-checador-staging.conf /etc/nginx/sites-available/checador-staging
ln -sf /etc/nginx/sites-available/checador-staging /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d checador.staging.valeexpress.mx
```

---

## Dos cosas que cambian de comportamiento en staging (no son fallos)

**El código QR ya no necesita que alguien escriba la IP a mano.** `QrTab.tsx` usa
`window.location.origin` cuando no está en localhost, así que el QR apuntará solo a
`https://checador.staging.valeexpress.mx`. El campo manual de IP solo aparece en localhost.

**La cámara en vivo empieza a funcionar.** `getUserMedia` exige contexto seguro. En la LAN
de la oficina (`http://192.168.x.x`) el navegador la bloquea y el código cae al respaldo de
`<input capture>`, que abre la cámara nativa. Con HTTPS en staging se activará la captura en
vivo. Ambos caminos ya están implementados, así que no hay nada que tocar; conviene saberlo
porque la pantalla se verá distinta.

---

## Deuda que este trabajo no resuelve

Sigue vigente lo que ya listaba `AUDITORIA.md` y que la compatibilidad con el servidor no
cambia: el PIN se guarda en texto plano, la sesión de admin manda la contraseña en cada
petición (bcrypt por request), no hay JWT, no hay tests ni CI, y las migraciones son
`create_all` más `ALTER TABLE IF NOT EXISTS` en el arranque en vez de Alembic.

Esto último merece un aviso concreto para staging: **el esquema se migra solo al arrancar**,
sin registro de versiones ni forma de revertir. Funciona para el alcance actual, pero
significa que un `up -d` con código nuevo altera la base sin preguntar.
