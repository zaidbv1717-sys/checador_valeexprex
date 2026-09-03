from sqlalchemy.orm import Session

from .. import models
from .common import PUNCH_TYPE_LABELS, fmt_hm, period_range

DOW_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def compute_photo_log(db: Session, period, anchor_date_str, emp_filter):
    start, end = period_range(period, anchor_date_str)

    q = db.query(models.Record).filter(models.Record.photo_path.isnot(None))
    if emp_filter and emp_filter != "all":
        q = q.filter(models.Record.employee_name == emp_filter)
    recs = q.order_by(models.Record.employee_name.asc(), models.Record.timestamp.asc()).all()

    log = []
    for r in recs:
        day = r.timestamp.date()
        if not (start <= day <= end):
            continue
        log.append({
            "employeeName": r.employee_name,
            "date": day.isoformat(),
            "dayLabel": DOW_NAMES[day.weekday()],
            "type": PUNCH_TYPE_LABELS.get(r.type, r.type),
            "time": fmt_hm(r.timestamp),
            "photoFile": r.photo_path,
        })
    return log
