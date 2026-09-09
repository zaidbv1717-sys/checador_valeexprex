import os
import re
import unicodedata

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import clock, crud, models, rate_limit, schemas
from ..alerts import check_device_alert
from ..config import settings
from ..database import get_db
from ..net import client_ip

router = APIRouter()

TYPES = ("entrada", "comida_salida", "comida_entrada", "salida")
TYPE_LABELS = {
    "entrada": "Entrada",
    "comida_salida": "Salida a comer",
    "comida_entrada": "Regreso de comer",
    "salida": "Salida",
}

ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

PIN_RE = re.compile(r"^\d{4}$")


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text or "empleado"


def _employee_by_pin(db: Session, pin: str):
    if not PIN_RE.match(pin or ""):
        return None
    return db.query(models.Employee).filter(models.Employee.pin == pin).first()


@router.get("/today")
def get_today(employeeId: str = "", db: Session = Depends(get_db)):
    recs = db.query(models.Record).filter(
        models.Record.employee_id == employeeId,
        func.date(models.Record.timestamp) == clock.today(),
    ).all()
    done = {r.type: r.timestamp.isoformat() for r in recs}
    return {"done": done}


@router.post("/verify-pin")
def verify_pin(request: Request, body: schemas.VerifyPinRequest, db: Session = Depends(get_db)):
    # Un PIN son 4 digitos: 10 000 combinaciones. Sin freno se prueban todas en
    # minutos, y acertar devuelve nombre e id, asi que tambien enumera la plantilla.
    key = f"pin:{client_ip(request)}"
    if rate_limit.is_locked(key):
        return JSONResponse(
            {"ok": False, "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )
    emp = _employee_by_pin(db, body.pin)
    if emp:
        rate_limit.reset(key)
        return {"ok": True, "employee": {"id": emp.id, "name": emp.name}}
    rate_limit.register_failure(key)
    return {"ok": False}


@router.post("/punch")
async def punch(
    request: Request,
    db: Session = Depends(get_db),
    pin: str = Form(""),
    type: str = Form(""),
    photo: UploadFile = File(...),
):
    """Registra una marca de asistencia.

    El empleado se deriva del PIN, nunca de un id que mande el cliente: antes este
    endpoint aceptaba `employeeId` y `employeeName` como campos de formulario y
    confiaba en ellos, asi que cualquiera podia marcar por otro con una sola
    llamada HTTP copiando su id.
    """
    ip = client_ip(request)
    key = f"punch:{ip}"
    if rate_limit.is_locked(key):
        return JSONResponse(
            {"ok": False, "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )

    emp = _employee_by_pin(db, pin)
    if not emp:
        rate_limit.register_failure(key)
        return JSONResponse({"ok": False, "error": "PIN incorrecto"}, status_code=401)
    rate_limit.reset(key)

    if type not in TYPES:
        return JSONResponse({"ok": False, "error": "tipo inválido"}, status_code=400)

    ext = ALLOWED_PHOTO_TYPES.get(photo.content_type)
    if not photo.filename or not ext:
        return JSONResponse({"ok": False, "error": "se requiere una foto para marcar"}, status_code=400)
    photo_bytes = await photo.read()
    if not photo_bytes:
        return JSONResponse({"ok": False, "error": "se requiere una foto para marcar"}, status_code=400)
    if len(photo_bytes) > settings.max_photo_bytes:
        limit_mb = settings.max_photo_bytes / (1024 * 1024)
        return JSONResponse(
            {"ok": False, "error": f"La foto es demasiado grande (máximo {limit_mb:.0f} MB)."},
            status_code=413,
        )

    now = clock.now()
    today_date = now.date()

    existing = db.query(models.Record).filter(
        models.Record.employee_id == emp.id,
        models.Record.type == type,
        func.date(models.Record.timestamp) == today_date,
    ).first()
    if existing:
        return JSONResponse(
            {"ok": False, "error": "Ese registro ya se marcó hoy. Solo el administrador puede modificarlo."},
            status_code=400,
        )

    step_index = TYPES.index(type)
    if step_index > 0:
        previous_type = TYPES[step_index - 1]
        done_previous = db.query(models.Record).filter(
            models.Record.employee_id == emp.id,
            models.Record.type == previous_type,
            func.date(models.Record.timestamp) == today_date,
        ).first()
        if not done_previous:
            return JSONResponse(
                {"ok": False, "error": f'Primero debes marcar "{TYPE_LABELS[previous_type]}".'},
                status_code=400,
            )

    record_id = crud.uid()
    photo_filename = f"{_slugify(emp.name)}_{type}_{now.strftime('%Y%m%d_%H%M%S')}_{record_id}{ext}"
    photo_full_path = os.path.join(settings.punch_photos_dir, photo_filename)
    os.makedirs(settings.punch_photos_dir, exist_ok=True)
    with open(photo_full_path, "wb") as f:
        f.write(photo_bytes)

    # Si el insert falla, la foto ya escrita quedaria huerfana ocupando disco sin
    # registro que la referencie.
    try:
        db.add(models.Record(
            id=record_id, employee_id=emp.id, employee_name=emp.name,
            type=type, timestamp=now, source_ip=ip, photo_path=photo_filename,
        ))
        db.commit()
    except Exception:
        db.rollback()
        if os.path.isfile(photo_full_path):
            os.remove(photo_full_path)
        raise

    if type == "entrada":
        check_device_alert(db, ip, emp.id, emp.name, now)

    return {"ok": True, "time": now.strftime("%H:%M:%S")}
