import os
import subprocess
import time
from datetime import datetime

from .config import settings


def backup_now():
    """Vuelca la base de datos Postgres (vía `docker compose exec`) a data/backups/
    con fecha y hora, y conserva solo los últimos MAX_BACKUPS. Best-effort: si Docker
    no está disponible no rompe el arranque del servidor, solo omite el respaldo."""
    os.makedirs(settings.backup_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(settings.backup_dir, f"attendance_{ts}.sql")
    try:
        with open(dest, "wb") as f:
            subprocess.run(
                ["docker", "compose", "exec", "-T", "postgres", "pg_dump", "-U", settings.postgres_user, settings.postgres_db],
                check=True, stdout=f, stderr=subprocess.DEVNULL,
                cwd=settings.compose_project_dir,
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
