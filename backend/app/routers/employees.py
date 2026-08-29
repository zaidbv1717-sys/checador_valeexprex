import re

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
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


@router.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    emps = db.query(models.Employee).order_by(models.Employee.name).all()
    return {"employees": [
        {
            "id": e.id, "name": e.name, "pin": e.pin,
            "sched_in": e.sched_in, "sched_out": e.sched_out,
            "category": e.category, "lunch_minutes": e.lunch_minutes,
        }
        for e in emps
    ]}


@router.get("/employee-categories")
def list_categories():
    return {"categories": [
        {"value": c, "label": CATEGORY_LABELS[c], **CATEGORY_DEFAULTS[c]}
        for c in EMPLOYEE_CATEGORIES
    ]}


@router.post("/employees")
def create_employee(body: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    pin = body.pin.strip()
    category = body.category if body.category in EMPLOYEE_CATEGORIES else "trabajador"
    defaults = CATEGORY_DEFAULTS[category]
    sched_in = body.schedIn or defaults["schedIn"]
    sched_out = body.schedOut or defaults["schedOut"]
    lunch_minutes = int(body.lunchMinutes) if body.lunchMinutes not in (None, "") else defaults["lunchMinutes"]
    if not name or not re.match(r"^\d{4}$", pin):
        return JSONResponse({"ok": False, "error": "nombre y PIN de 4 dígitos requeridos"}, status_code=400)
    if db.query(models.Employee).filter(models.Employee.pin == pin).first():
        return JSONResponse({"ok": False, "error": "ese PIN ya está en uso"}, status_code=400)
    db.add(models.Employee(
        id=crud.uid(), name=name, pin=pin, sched_in=sched_in, sched_out=sched_out,
        category=category, lunch_minutes=lunch_minutes,
    ))
    db.commit()
    return {"ok": True}


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: str, db: Session = Depends(get_db)):
    db.query(models.Employee).filter(models.Employee.id == employee_id).delete()
    db.commit()
    return {"ok": True}
