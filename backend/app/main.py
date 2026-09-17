import socket
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from . import clock, crud, security
from .backup import backup_loop, backup_now
from .config import REPO_ROOT, settings
from .database import Base, SessionLocal, engine
from .routers import auth, calendar, device_alerts, employees, justifications, public, records

# `/docs` (y su `/openapi.json`, que es de donde salen los datos) se apagan con
# DOCS_ENABLED=false. En la LAN de la oficina no estorban; en un servidor
# alcanzable desde internet publican el mapa entero de la API, endpoints de
# admin incluidos, a cualquiera que pase. Ver .env.staging.example.
app = FastAPI(
    title="Reloj Checador API",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

# CORS_ORIGINS acota quien puede llamar a la API desde otro origen. El default
# sigue siendo "*" para no romper la instalacion de la oficina (LAN de
# confianza); en staging/produccion se fija el dominio real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(justifications.router, prefix="/api")
app.include_router(device_alerts.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        # Migración: employees/records creados antes de requerir foto no tienen esta columna.
        conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS photo_path VARCHAR"))
        conn.execute(text("ALTER TABLE records ADD COLUMN IF NOT EXISTS photo_path VARCHAR"))
        # Migración: datos de perfil agregados despues del alta inicial de empleados.
        conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS phone VARCHAR"))
        conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS email VARCHAR"))
        conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS emergency_contact VARCHAR"))
        conn.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS medical_history TEXT"))
        # Una sola marca de cada tipo por empleado y dia. Antes esto vivia solo en
        # codigo (consultar-luego-insertar), que no protege contra dos peticiones
        # simultaneas. SQLAlchemy no puede declarar un indice sobre date(timestamp),
        # asi que va en crudo.
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_records_employee_type_day "
            "ON records (employee_id, type, (timestamp::date))"
        ))
    db = SessionLocal()
    try:
        cfg = crud.get_config(db)
        if "password" not in cfg:
            crud.set_config(db, {"password": security.hash_password(settings.default_admin_password)})
        if "lunch_minutes" not in cfg:
            crud.set_config(db, {"lunch_minutes": "90"})
        if "recovery_code" not in cfg:
            crud.set_config(db, {"recovery_code": crud.gen_recovery_code()})
        cfg = crud.get_config(db)
        using_default_password = security.verify_password(
            settings.default_admin_password, cfg.get("password", "")
        )
    finally:
        db.close()

    backup_now()
    threading.Thread(target=backup_loop, daemon=True).start()

    ip = get_local_ip()
    print("=" * 56)
    print(" Reloj checador — servidor iniciado (FastAPI + PostgreSQL)")
    print(f" En esta computadora:   http://localhost:{settings.port}")
    print(f" Para el QR (celulares): http://{ip}:{settings.port}")
    print(" (los celulares deben estar en la misma red WiFi)")
    print(f" Zona horaria de la oficina: {settings.office_tz} (hora local: {clock.now():%H:%M})")
    # El codigo de recuperacion ya no se imprime: `docker logs` es legible por
    # cualquiera con acceso a la maquina, y ese codigo restablece la contrasena.
    # Se consulta desde el panel de admin, en Config.
    if using_default_password:
        print(" AVISO: la contraseña de administrador es la de fábrica. Cámbiala en el panel.")
    print(f" Respaldo automático diario en: data/backups/ (se guardan los últimos {settings.max_backups})")
    print("=" * 56)


FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
