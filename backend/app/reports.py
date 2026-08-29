import calendar
import csv
import io
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import crud, models

CATEGORY_LABELS = {
    "practicante": "Practicante",
    "trabajador": "Trabajador",
    "administrador": "Administrador",
}

JUSTIFICATION_TYPE_LABELS = {
    "medica": "Médica / fuerza mayor",
    "personal": "Personal",
    "permiso_economico": "Permiso económico",
    "vacaciones": "Vacaciones",
}


def period_range(period, anchor_date_str):
    if anchor_date_str:
        anchor = datetime.strptime(anchor_date_str, "%Y-%m-%d").date()
    else:
        anchor = datetime.now().date()
    if period == "semana":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        return start, end
    if period == "mes":
        start = anchor.replace(day=1)
        if anchor.month == 12:
            end = anchor.replace(year=anchor.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = anchor.replace(month=anchor.month + 1, day=1) - timedelta(days=1)
        return start, end
    return anchor, anchor


def fmt_hm(ts):
    if not ts:
        return None
    return ts.strftime("%H:%M")


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
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


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


def build_csv(db: Session, rows, period, date_str, emp_filter):
    period_label = {"dia": "Día", "semana": "Semana", "mes": "Mes"}.get(period, period)
    emp_label = "Todos" if (not emp_filter or emp_filter == "all") else emp_filter
    anchor = date_str or datetime.now().strftime("%Y-%m-%d")

    categories = {e.id: e.category for e in db.query(models.Employee).all()}

    dow_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Reporte de Asistencia — Reloj Checador"])
    w.writerow([
        f"Periodo: {period_label}",
        f'Fecha de referencia: {datetime.strptime(anchor, "%Y-%m-%d").strftime("%d/%m/%Y")}',
        f"Empleado: {emp_label}",
        f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}',
    ])
    w.writerow([])
    w.writerow(["Empleado", "Categoría", "Fecha", "Entrada", "Salida a comer", "Regreso de comer", "Salida", "Horas trabajadas", "Estado"])

    sorted_rows = sorted(rows, key=lambda r: (r["employeeName"], r["date"]))
    current_emp = None
    emp_hours = emp_extra = 0.0
    emp_retardos = emp_missing = 0

    def flush_subtotal():
        if current_emp is not None:
            w.writerow([
                f"Subtotal {current_emp}", "", "", "", "", "", "",
                f"{emp_hours:.2f} h",
                f"{emp_retardos} retardo(s) · {emp_extra:.2f} h extra · {emp_missing} sin marca",
            ])
            w.writerow([])

    for r in sorted_rows:
        if current_emp is not None and r["employeeName"] != current_emp:
            flush_subtotal()
            emp_hours = emp_extra = 0.0
            emp_retardos = emp_missing = 0
        current_emp = r["employeeName"]
        emp_hours += r["hours"]
        emp_extra += r["extraHrs"]
        if r["retardoMin"] > 0:
            emp_retardos += 1
        if r["missing"]:
            emp_missing += 1

        fecha_dt = datetime.strptime(r["date"], "%Y-%m-%d")
        fecha = f"{dow_names[fecha_dt.weekday()]} {fecha_dt.strftime('%d/%m/%Y')}"
        cat = CATEGORY_LABELS.get(categories.get(r["employeeId"]), "")
        estado_parts = []
        if r["missing"]:
            estado_parts.append("Sin marca")
        if r["retardoMin"] > 0:
            estado_parts.append(f"Retardo {r['retardoMin']} min")
        if r["extraHrs"] > 0:
            estado_parts.append(f"Extra {r['extraHrs']:.1f} h")
        if r["lunchLateMin"] > 0:
            estado_parts.append(f"Comida +{r['lunchLateMin']} min")
        estado = " | ".join(estado_parts) if estado_parts else "Normal"

        w.writerow([
            r["employeeName"], cat, fecha,
            r["entrada"] or "—", r["comida_salida"] or "—", r["comida_entrada"] or "—", r["salida"] or "—",
            f"{r['hours']:.2f} h", estado,
        ])
    flush_subtotal()

    total_hours = sum(r["hours"] for r in rows)
    total_extra = sum(r["extraHrs"] for r in rows)
    total_retardos = sum(1 for r in rows if r["retardoMin"] > 0)
    total_missing = sum(1 for r in rows if r["missing"])
    w.writerow([
        "TOTAL GENERAL", "", "", "", "", "", "",
        f"{total_hours:.2f} h",
        f"{total_retardos} retardo(s) · {total_extra:.2f} h extra · {total_missing} sin marca",
    ])

    return ("﻿" + buf.getvalue()).encode("utf-8")
