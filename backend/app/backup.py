import os
import subprocess
import time
from datetime import datetime

from .config import settings


def backup_now():
    """Vuelca la base de datos Postgres a data/backups/ con fecha y hora (vía `pg_dump`,
    conectándose directamente a DATABASE_URL), y conserva solo los últimos MAX_BACKUPS.
    Best-effort: si `pg_dump` no está disponible no rompe el arranque del servidor, solo
    omite el respaldo. Dentro del contenedor del backend `pg_dump` siempre está instalado
    (ver Dockerfile); fuera de Docker (venv local en Windows) puede no estarlo."""
    os.makedirs(settings.backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(settings.backup_dir, f"attendance_{ts}.sql")
    try:
        subprocess.run(
            ["pg_dump", settings.database_url, "-f", dest],
            check=True, capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        if os.path.exists(dest):
            os.remove(dest)
        return None

    existing = sorted(f for f in os.listdir(settings.backup_dir) if f.startswith("attendance_") and f.endswith(".sql"))
    while len(existing) > settings.max_backups:
        os.remove(os.path.join(settings.backup_dir, existing.pop(0)))
    return dest


def backup_loop():
    while True:
        time.sleep(24 * 60 * 60)  # cada 24 horas
        try:
            backup_now()
        except Exception:
            pass
