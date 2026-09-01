from datetime import datetime

from sqlalchemy.orm import Session

from .. import crud, models
from .common import fmt_hm, period_range


def _photo_url(rec):
    return f"/api/admin/records/{rec.id}/photo" if (rec and rec.photo_path) else None


def compute_report_rows(db: Session, period, anchor_date_str, emp_filter):
    employees = {e.id: e for e in db.query(models.Employee).all()}
    cfg = crud.get_config(db)
    default_lunch_minutes = int(cfg.get("lunch_minutes", "90") or 90)
    recs = db.query(models.Record).order_by(models.Record.timestamp.asc()).all()
    notes = {(n.employee_id, n.date): n.note for n in db.query(models.DayNote).all()}

    by_key = {}
    for r in recs:
        day = r.timestamp.date()
        key = (r.employee_id, day)
        if key not in by_key:
            by_key[key] = {
                "employee_id": r.employee_id, "employee_name": r.employee_name, "date": day,
                "entrada": None, "comida_salida": None, "comida_entrada": None, "salida": None,
            }
        by_key[key][r.type] = r

    today = datetime.now().date()
    start, end = period_range(period, anchor_date_str)

    rows = []
    for g in by_key.values():
        if not (start <= g["date"] <= end):
            continue
        if emp_filter and emp_filter != "all" and g["employee_name"] != emp_filter:
            continue
        emp = employees.get(g["employee_id"])
        sched_in = emp.sched_in if emp else ""
        sched_out = emp.sched_out if emp else ""
        lunch_minutes = emp.lunch_minutes if (emp and emp.lunch_minutes is not None) else default_lunch_minutes

        hours = 0.0
        if g["entrada"] and g["salida"]:
            t_in = g["entrada"].timestamp
            t_out = g["salida"].timestamp
            worked = (t_out - t_in).total_seconds() / 3600
            lunch_h = 0.0
            if g["comida_salida"] and g["comida_entrada"]:
                lo = g["comida_salida"].timestamp
                li = g["comida_entrada"].timestamp
                lunch_h = max(0, (li - lo).total_seconds() / 3600)
            hours = max(0, worked - lunch_h)

        retardo_min = 0
        if g["entrada"] and sched_in:
            h, m = map(int, sched_in.split(":"))
            sched_dt = datetime.combine(g["date"], datetime.min.time()).replace(hour=h, minute=m)
            t_in = g["entrada"].timestamp
            diff = (t_in - sched_dt).total_seconds() / 60
            if diff > 10:
                retardo_min = round(diff)

        lunch_late_min = 0
        if g["comida_salida"] and g["comida_entrada"]:
            lo = g["comida_salida"].timestamp
            li = g["comida_entrada"].timestamp
            taken = (li - lo).total_seconds() / 60
            if taken > lunch_minutes + 5:
                lunch_late_min = round(taken - lunch_minutes)

        extra_hrs = 0.0
        if g["entrada"] and g["salida"] and sched_in and sched_out:
            h1, m1 = map(int, sched_in.split(":"))
            h2, m2 = map(int, sched_out.split(":"))
            sched_hrs = (h2 + m2 / 60) - (h1 + m1 / 60)
            if sched_hrs < 0:
                sched_hrs += 24
            diff_extra = hours - sched_hrs
            if diff_extra > 0.1:
                extra_hrs = diff_extra

        is_past = g["date"] != today
        missing = bool(is_past and ((g["entrada"] and not g["salida"]) or (not g["entrada"] and g["salida"])))

        rows.append({
            "employeeId": g["employee_id"], "employeeName": g["employee_name"],
            "date": g["date"].isoformat(),
            "entrada": fmt_hm(g["entrada"].timestamp if g["entrada"] else None),
            "comida_salida": fmt_hm(g["comida_salida"].timestamp if g["comida_salida"] else None),
            "comida_entrada": fmt_hm(g["comida_entrada"].timestamp if g["comida_entrada"] else None),
            "salida": fmt_hm(g["salida"].timestamp if g["salida"] else None),
            "hours": round(hours, 2), "retardoMin": retardo_min, "extraHrs": round(extra_hrs, 2),
            "lunchLateMin": lunch_late_min, "missing": missing,
            "note": notes.get((g["employee_id"], g["date"].isoformat()), "") or "",
            "entradaPhotoUrl": _photo_url(g["entrada"]),
            "comidaSalidaPhotoUrl": _photo_url(g["comida_salida"]),
            "comidaEntradaPhotoUrl": _photo_url(g["comida_entrada"]),
            "salidaPhotoUrl": _photo_url(g["salida"]),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
