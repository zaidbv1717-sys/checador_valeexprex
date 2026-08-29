import socket
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import crud, security
from .backup import backup_loop, backup_now
from .config import REPO_ROOT, settings
from .database import Base, SessionLocal, engine
from .routers import auth, calendar, device_alerts, employees, justifications, public, records

app = FastAPI(title="Reloj Checador API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    print(f' Código de recuperación de contraseña: {cfg.get("recovery_code", "")}')
    print(" (guárdalo en un lugar seguro — sirve si olvidas la contraseña de admin)")
    print(f" Respaldo automático diario en: data/backups/ (se guardan los últimos {settings.max_backups})")
    print("=" * 56)


FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
