# Reloj Checador — ValeExpress

Sistema de registro de asistencia (checador) sin cámara, pensado para operar dentro de una
red WiFi local: los empleados escanean un código QR desde su celular y marcan su entrada,
salida a comer, regreso y salida con un PIN de 4 dígitos.

## Stack

- **PostgreSQL** — base de datos.
- **FastAPI** (Python) — API backend.
- **React + TypeScript** (Vite) — frontend.
- **Node** — tooling de build del frontend.

El código anterior (Python estándar + SQLite + HTML/JS plano) quedó archivado en
[`legacy/`](legacy/) como referencia; ya no se ejecuta.

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Para desarrollo activo (opcional): Python 3.11+ y Node.js 20+

## Opción 1 — Todo en Docker (más simple)

Levanta PostgreSQL, el backend y el frontend, cada uno en su propio contenedor:

```bash
docker compose up -d --build
```

- Frontend (nginx sirviendo el build de React): `http://localhost` — esta es la URL que
  va en el código QR (pestaña "Código QR" del panel admin), y la que abren los empleados
  desde su celular en la misma red WiFi.
- Backend (API directa, útil para depurar): `http://localhost:8000` (docs interactivas en
  `/docs`).

`--build` solo hace falta la primera vez o después de cambiar código; luego basta con
`docker compose up -d`. Para bajar todo: `docker compose down` (los datos persisten); para
borrar también los datos: `docker compose down -v`.

## Opción 2 — Desarrollo local (hot reload)

Útil mientras se edita código, ya que evita reconstruir imágenes en cada cambio.

1. **Base de datos** — desde la raíz del repo:

   ```bash
   docker compose up -d postgres
   ```

2. **Backend**:

   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   copy .env.example .env     # si no existe ya
   uvicorn app.main:app --reload --port 8000
   ```

3. **Frontend** (en otra terminal):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Abre `http://localhost:5173`. Vite redirige las llamadas `/api/*` al backend en el
   puerto 8000 (ver `frontend/vite.config.ts`), así que el código del frontend usa las
   mismas rutas relativas sin importar el entorno.

Alternativa sin contenedores para el día a día: compilar el frontend una vez
(`cd frontend && npm run build`) y dejar que el propio backend lo sirva desde
`http://localhost:8000` — así funciona [`iniciar_reloj_checador.bat`](iniciar_reloj_checador.bat).
Hay que repetir el `npm run build` después de cada cambio de frontend para que se refleje.

## Configuración

Variables de entorno del backend (`backend/.env`, ver `backend/.env.example`; en Docker se
pasan como `environment:` en `docker-compose.yml`):

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql://reloj:reloj@localhost:5432/reloj_checador` |
| `PORT` | Puerto del backend | `8000` |
| `MAX_BACKUPS` | Respaldos diarios a conservar | `30` |
| `DEVICE_ALERT_WINDOW_MIN` | Ventana (minutos) para detectar dispositivo compartido | `5` |
| `DEFAULT_ADMIN_PASSWORD` | Contraseña de admin sembrada la primera vez que arranca | `1234` |

El respaldo automático corre una vez al día (y también al arrancar) usando `pg_dump`
contra `DATABASE_URL` directamente, volcando a `data/backups/`. Dentro del contenedor del
backend `pg_dump` viene incluido (ver `backend/Dockerfile`); si corres el backend fuera de
Docker (Opción 2) y no tienes el cliente de PostgreSQL instalado, el respaldo simplemente
se omite sin romper el arranque.

## Estructura

```
backend/     API FastAPI + modelos SQLAlchemy + lógica de reportes (Dockerfile propio)
frontend/    App React + TypeScript (Vite), servida por nginx en su contenedor (Dockerfile propio)
legacy/      Versión anterior (Python stdlib + SQLite), archivada
docker-compose.yml   postgres + backend + frontend
```
