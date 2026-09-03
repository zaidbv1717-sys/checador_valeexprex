import os
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import crud, models, reports, schemas
from ..config import settings
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["records"], dependencies=[Depends(require_admin)])

TYPES = ("entrada", "comida_salida", "comida_entrada", "salida")


@router.get("/records/{record_id}/photo")
def get_record_photo(record_id: str, db: Session = Depends(get_db)):
    rec = db.get(models.Record, record_id)
    if not rec or not rec.photo_path:
        return JSONResponse({"error": "not found"}, status_code=404)
    path = os.path.join(settings.punch_photos_dir, rec.photo_path)
    if not os.path.isfile(path):
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path)


@router.get("/records")
def get_records(period: str = "dia", date: str = "", emp: str = "all", db: Session = Depends(get_db)):
    rows = reports.compute_report_rows(db, period, date, emp)
    return {"rows": rows}


@router.get("/absences")
def get_absences(period: str = "dia", date: str = "", emp: str = "all", db: Session = Depends(get_db)):
    absences = reports.compute_absences(db, period, date, emp)
    return {"absences": absences}


@router.get("/export.xlsx")
def export_xlsx(period: str = "mes", date: str = "", emp: str = "all", db: Session = Depends(get_db)):
    rows = reports.compute_report_rows(db, period, date, emp)
    absences = reports.compute_absences(db, period, date, emp)
    photo_log = reports.compute_photo_log(db, period, date, emp)
    data = reports.build_xlsx(db, rows, absences, photo_log, period, date, emp)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="registros_asistencia.xlsx"'},
    )


@router.post("/manual-edit")
def manual_edit(body: schemas.ManualEditRequest, db: Session = Depends(get_db)):
    for ptype, hm in (body.edits or {}).items():
        if not hm or ptype not in TYPES:
            continue
        h, m = map(int, hm.split(":"))
        ts = datetime.strptime(body.dateStr, "%Y-%m-%d").replace(hour=h, minute=m)
        existing = db.query(models.Record).filter(
            models.Record.employee_id == body.employeeId,
            models.Record.type == ptype,
            func.date(models.Record.timestamp) == ts.date(),
        ).first()
        if existing:
            existing.timestamp = ts
        else:
            db.add(models.Record(
                id=crud.uid(), employee_id=body.employeeId, employee_name=body.employeeName,
                type=ptype, timestamp=ts, source_ip=None,
            ))

    if body.note is not None:
        note_val = (body.note or "").strip()
        day_note = db.query(models.DayNote).filter(
            models.DayNote.employee_id == body.employeeId,
            models.DayNote.date == body.dateStr,
        ).first()
        if note_val:
            if day_note:
                day_note.note = note_val
            else:
                db.add(models.DayNote(employee_id=body.employeeId, date=body.dateStr, note=note_val))
        elif day_note:
            db.delete(day_note)

    db.commit()
    return {"ok": True}
