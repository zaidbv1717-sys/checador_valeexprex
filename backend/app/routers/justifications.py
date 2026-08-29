from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["justifications"], dependencies=[Depends(require_admin)])

JUSTIFICATION_TYPES = ("medica", "personal", "permiso_economico", "vacaciones")
JUSTIFICATION_STATUSES = ("pendiente", "aprobada", "rechazada")


@router.get("/justifications")
def list_justifications(emp: str = "all", db: Session = Depends(get_db)):
    q = db.query(models.Justification)
    if emp and emp != "all":
        q = q.filter(models.Justification.employee_name == emp)
    items = q.order_by(models.Justification.date_start.desc()).all()
    return {"justifications": [
        {
            "id": j.id, "employee_id": j.employee_id, "employee_name": j.employee_name,
            "date_start": j.date_start, "date_end": j.date_end, "type": j.type,
            "status": j.status, "note": j.note,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in items
    ]}


@router.post("/justifications")
def create_justification(body: schemas.JustificationCreate, db: Session = Depends(get_db)):
    date_end = body.dateEnd or body.dateStart
    note = (body.note or "").strip()
    if not body.employeeId or not body.dateStart or body.type not in JUSTIFICATION_TYPES or body.status not in JUSTIFICATION_STATUSES:
        return JSONResponse({"ok": False, "error": "Faltan datos o son inválidos"}, status_code=400)
    if date_end < body.dateStart:
        return JSONResponse({"ok": False, "error": "La fecha final no puede ser antes de la inicial"}, status_code=400)
    db.add(models.Justification(
        id=crud.uid(), employee_id=body.employeeId, employee_name=body.employeeName,
        date_start=body.dateStart, date_end=date_end, type=body.type, status=body.status,
        note=note, created_at=datetime.now(),
    ))
    db.commit()
    return {"ok": True}


@router.post("/justifications/status")
def update_justification_status(body: schemas.JustificationStatusUpdate, db: Session = Depends(get_db)):
    if body.status not in JUSTIFICATION_STATUSES:
        return JSONResponse({"ok": False, "error": "Estado inválido"}, status_code=400)
    j = db.get(models.Justification, body.id)
    if j:
        j.status = body.status
        db.commit()
    return {"ok": True}


@router.delete("/justifications/{justification_id}")
def delete_justification(justification_id: str, db: Session = Depends(get_db)):
    db.query(models.Justification).filter(models.Justification.id == justification_id).delete()
    db.commit()
    return {"ok": True}
