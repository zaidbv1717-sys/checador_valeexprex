from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from .common import JUSTIFICATION_TYPE_LABELS, period_range


def compute_absences(db: Session, period, anchor_date_str, emp_filter):
    employees = db.query(models.Employee).all()
    if emp_filter and emp_filter != "all":
        employees = [e for e in employees if e.name == emp_filter]
    start, end = period_range(period, anchor_date_str)
    today = datetime.now().date()
    effective_end = min(end, today - timedelta(days=1))

    absences = []
    if effective_end >= start:
        d = start
        while d <= effective_end:
            if d.weekday() != 6:  # 6 = domingo
                for emp in employees:
                    has_entry = db.query(models.Record).filter(
                        models.Record.employee_id == emp.id,
                        models.Record.type == "entrada",
                        func.date(models.Record.timestamp) == d,
                    ).first()
                    if has_entry:
                        continue
                    just = db.query(models.Justification).filter(
                        models.Justification.employee_id == emp.id,
                        models.Justification.status == "aprobada",
                        models.Justification.date_start <= d.isoformat(),
                        models.Justification.date_end >= d.isoformat(),
                    ).first()
                    absences.append({
                        "employeeId": emp.id, "employeeName": emp.name, "date": d.isoformat(),
                        "justified": bool(just),
                        "justificationType": JUSTIFICATION_TYPE_LABELS.get(just.type, just.type) if just else None,
                    })
            d += timedelta(days=1)
    return absences
