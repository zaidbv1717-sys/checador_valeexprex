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

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para PostgreSQL en desarrollo)
- Python 3.11+
- Node.js 20+

## Puesta en marcha (desarrollo)

1. **Base de datos** — desde la raíz del repo:

   ```bash
   docker compose up -d
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

   La API queda en `http://localhost:8000` (documentación interactiva en `/docs`).

3. **Frontend** (en otra terminal):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Abre `http://localhost:5173`. Vite redirige las llamadas `/api/*` al backend en el
   puerto 8000 (ver `frontend/vite.config.ts`), así que el código del frontend usa las
   mismas rutas relativas sin importar el entorno.

## Uso normal (un solo comando)

Una vez compilado el frontend, FastAPI sirve la aplicación completa desde un único
puerto — igual que la versión anterior:

```bash
cd frontend && npm run build
cd ../backend && uvicorn app.main:app --port 8000
```

Abre `http://localhost:8000` en esta computadora, o la IP de red que imprime la consola
al arrancar (esa es la URL que va en el código QR — pestaña "Código QR" del panel admin).
También puedes usar [`iniciar_reloj_checador.bat`](iniciar_reloj_checador.bat) para
levantar Postgres y el backend con un doble clic (requiere haber hecho `npm run build`
al menos una vez, o tras cada cambio de frontend).

## Configuración

Variables de entorno del backend (`backend/.env`, ver `backend/.env.example`):

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL | `postgresql://reloj:reloj@localhost:5432/reloj_checador` |
| `POSTGRES_USER` / `POSTGRES_DB` | Usados por el respaldo automático (`docker compose exec`) | `reloj` / `reloj_checador` |
| `PORT` | Puerto del backend | `8000` |
| `MAX_BACKUPS` | Respaldos diarios a conservar | `30` |
| `DEVICE_ALERT_WINDOW_MIN` | Ventana (minutos) para detectar dispositivo compartido | `5` |
| `DEFAULT_ADMIN_PASSWORD` | Contraseña de admin sembrada la primera vez que arranca | `1234` |

El respaldo automático corre una vez al día y usa `docker compose exec postgres pg_dump`
para volcar la base a `data/backups/`, sin requerir un cliente de PostgreSQL instalado en
Windows — solo Docker Desktop corriendo.

## Estructura

```
backend/     API FastAPI + modelos SQLAlchemy + lógica de reportes
frontend/    App React + TypeScript (Vite)
legacy/      Versión anterior (Python stdlib + SQLite), archivada
docker-compose.yml   PostgreSQL para desarrollo
```
