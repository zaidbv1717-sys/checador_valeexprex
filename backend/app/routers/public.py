from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..alerts import check_device_alert
from ..database import get_db

router = APIRouter()

TYPES = ("entrada", "comida_salida", "comida_entrada", "salida")
TYPE_LABELS = {
    "entrada": "Entrada",
    "comida_salida": "Salida a comer",
    "comida_entrada": "Regreso de comer",
    "salida": "Salida",
}


@router.get("/today")
def get_today(employeeId: str = "", db: Session = Depends(get_db)):
    today_date = datetime.now().date()
    recs = db.query(models.Record).filter(
        models.Record.employee_id == employeeId,
        func.date(models.Record.timestamp) == today_date,
    ).all()
    done = {r.type: r.timestamp.isoformat() for r in recs}
    return {"done": done}


@router.post("/verify-pin")
def verify_pin(body: schemas.VerifyPinRequest, db: Session = Depends(get_db)):
    emp = db.query(models.Employee).filter(models.Employee.pin == body.pin).first()
    if emp:
        return {"ok": True, "employee": {"id": emp.id, "name": emp.name}}
    return {"ok": False}


@router.post("/punch")
def punch(body: schemas.PunchRequest, request: Request, db: Session = Depends(get_db)):
    if body.type not in TYPES:
        return JSONResponse({"ok": False, "error": "tipo inválido"}, status_code=400)

    client_ip = request.client.host if request.client else ""
    now = datetime.now()
    today_date = now.date()

    existing = db.query(models.Record).filter(
        models.Record.employee_id == body.employeeId,
        models.Record.type == body.type,
        func.date(models.Record.timestamp) == today_date,
    ).first()
    if existing:
        return JSONResponse(
            {"ok": False, "error": "Ese registro ya se marcó hoy. Solo el administrador puede modificarlo."},
            status_code=400,
        )

    step_index = TYPES.index(body.type)
    if step_index > 0:
        previous_type = TYPES[step_index - 1]
        done_previous = db.query(models.Record).filter(
            models.Record.employee_id == body.employeeId,
            models.Record.type == previous_type,
            func.date(models.Record.timestamp) == today_date,
        ).first()
        if not done_previous:
            return JSONResponse(
                {"ok": False, "error": f'Primero debes marcar "{TYPE_LABELS[previous_type]}".'},
                status_code=400,
            )

    db.add(models.Record(
        id=crud.uid(), employee_id=body.employeeId, employee_name=body.employeeName,
        type=body.type, timestamp=now, source_ip=client_ip,
    ))
    db.commit()

    if body.type == "entrada":
        check_device_alert(db, client_ip, body.employeeId, body.employeeName, now)

    return {"ok": True, "time": now.strftime("%H:%M:%S")}
