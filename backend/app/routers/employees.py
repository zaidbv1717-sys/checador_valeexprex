import os
import re

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from .. import crud, models
from ..config import settings
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["employees"], dependencies=[Depends(require_admin)])

EMPLOYEE_CATEGORIES = ("practicante", "trabajador", "administrador")
CATEGORY_LABELS = {
    "practicante": "Practicante",
    "trabajador": "Trabajador",
    "administrador": "Administrador",
}
CATEGORY_DEFAULTS = {
    "practicante": {"schedIn": "10:00", "schedOut": "18:00", "lunchMinutes": 90},
    "trabajador": {"schedIn": "08:30", "schedOut": "18:00", "lunchMinutes": 90},
    "administrador": {"schedIn": "08:30", "schedOut": "19:00", "lunchMinutes": 90},
}

ALLOWED_PHOTO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _photo_url(emp: models.Employee):
    return f"/api/admin/employees/{emp.id}/photo" if emp.photo_path else None


@router.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    emps = db.query(models.Employee).order_by(models.Employee.name).all()
    return {"employees": [
        {
            "id": e.id, "name": e.name, "pin": e.pin,
            "sched_in": e.sched_in, "sched_out": e.sched_out,
            "category": e.category, "lunch_minutes": e.lunch_minutes,
            "photoUrl": _photo_url(e),
        }
        for e in emps
    ]}


@router.get("/employee-categories")
def list_categories():
    return {"categories": [
        {"value": c, "label": CATEGORY_LABELS[c], **CATEGORY_DEFAULTS[c]}
        for c in EMPLOYEE_CATEGORIES
    ]}


@router.get("/employees/{employee_id}/photo")
def get_employee_photo(employee_id: str, db: Session = Depends(get_db)):
    emp = db.get(models.Employee, employee_id)
    if not emp or not emp.photo_path:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = os.path.join(settings.photos_dir, emp.photo_path)
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


@router.post("/employees")
async def create_employee(
    db: Session = Depends(get_db),
    name: str = Form(""),
    pin: str = Form(""),
    category: str = Form("trabajador"),
    schedIn: str = Form(""),
    schedOut: str = Form(""),
    lunchMinutes: str = Form(""),
    photo: UploadFile = File(...),
):
    name = name.strip()
    pin = pin.strip()
    category = category if category in EMPLOYEE_CATEGORIES else "trabajador"
    defaults = CATEGORY_DEFAULTS[category]
    sched_in = schedIn or defaults["schedIn"]
    sched_out = schedOut or defaults["schedOut"]
    lunch_minutes = int(lunchMinutes) if lunchMinutes not in (None, "") else defaults["lunchMinutes"]
    if not name or not re.match(r"^\d{4}$", pin):
        return JSONResponse({"ok": False, "error": "nombre y PIN de 4 dígitos requeridos"}, status_code=400)
    if db.query(models.Employee).filter(models.Employee.pin == pin).first():
        return JSONResponse({"ok": False, "error": "ese PIN ya está en uso"}, status_code=400)
    ext = ALLOWED_PHOTO_TYPES.get(photo.content_type)
    if not photo.filename or not ext:
        return JSONResponse({"ok": False, "error": "se requiere una foto (JPG, PNG o WEBP)"}, status_code=400)

    photo_bytes = await photo.read()
    if not photo_bytes:
        return JSONResponse({"ok": False, "error": "se requiere una foto (JPG, PNG o WEBP)"}, status_code=400)

    employee_id = crud.uid()
    photo_filename = f"{employee_id}{ext}"
    os.makedirs(settings.photos_dir, exist_ok=True)
    with open(os.path.join(settings.photos_dir, photo_filename), "wb") as f:
        f.write(photo_bytes)

    db.add(models.Employee(
        id=employee_id, name=name, pin=pin, sched_in=sched_in, sched_out=sched_out,
        category=category, lunch_minutes=lunch_minutes, photo_path=photo_filename,
    ))
    db.commit()
    return {"ok": True}


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.get(models.Employee, employee_id)
    if emp and emp.photo_path:
        photo_file = os.path.join(settings.photos_dir, emp.photo_path)
        if os.path.isfile(photo_file):
            os.remove(photo_file)
    db.query(models.Employee).filter(models.Employee.id == employee_id).delete()
    db.commit()
    return {"ok": True}
