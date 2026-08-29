import calendar
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models


def compute_calendar(db: Session, employee_id, year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    today = datetime.now().date()
    days = []
    for day_num in range(1, days_in_month + 1):
        d = datetime(year, month, day_num).date()
        has_entry = db.query(models.Record).filter(
            models.Record.employee_id == employee_id,
            models.Record.type == "entrada",
            func.date(models.Record.timestamp) == d,
        ).first()
        if has_entry:
            status = "asistio"
        elif d.weekday() == 6:
            status = "no_laboral"
        elif d >= today:
            status = "no_laboral"
        else:
            just = db.query(models.Justification).filter(
                models.Justification.employee_id == employee_id,
                models.Justification.status == "aprobada",
                models.Justification.date_start <= d.isoformat(),
                models.Justification.date_end >= d.isoformat(),
            ).first()
            status = "justificado" if just else "falta"
        days.append({"day": day_num, "date": d.isoformat(), "weekday": d.weekday(), "status": status})
    return days
