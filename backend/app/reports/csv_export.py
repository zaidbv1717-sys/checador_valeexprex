import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from .common import CATEGORY_LABELS, JUSTIFICATION_TYPE_LABELS


def _merge_absences(rows, absences):
    merged = list(rows)
    for a in absences:
        merged.append({
            "employeeId": a["employeeId"], "employeeName": a["employeeName"], "date": a["date"],
            "entrada": None, "comida_salida": None, "comida_entrada": None, "salida": None,
            "hours": 0.0, "retardoMin": 0, "lunchLateMin": 0, "missing": True,
            "note": "",
            "justified": a["justified"],
            "justificationType": JUSTIFICATION_TYPE_LABELS.get(a["justificationType"], a["justificationType"]) if a["justificationType"] else None,
        })
    return merged


def build_csv(db: Session, rows, absences, period, date_str, emp_filter):
    period_label = {"dia": "Día", "semana": "Semana", "mes": "Mes"}.get(period, period)
    emp_label = "Todos" if (not emp_filter or emp_filter == "all") else emp_filter
    anchor = date_str or datetime.now().strftime("%Y-%m-%d")

    categories = {e.id: e.category for e in db.query(models.Employee).all()}

    dow_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    HEADER = [
        "Empleado", "Categoría", "Fecha", "Día",
        "Entrada", "Salida a comer", "Regreso de comer", "Salida",
        "Horas trabajadas", "Retardo (min)", "Comida tarde (min)", "Sin marca", "Justificante",
    ]
    COLS = len(HEADER)

    all_rows = _merge_absences(rows, absences)

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Reporte de Asistencia — Reloj Checador"])
    w.writerow([f"Periodo: {period_label}"])
    w.writerow([f'Fecha de referencia: {datetime.strptime(anchor, "%Y-%m-%d").strftime("%d/%m/%Y")}'])
    w.writerow([f"Empleado: {emp_label}"])
    w.writerow([f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}'])
    w.writerow([])
    w.writerow(HEADER)

    sorted_rows = sorted(all_rows, key=lambda r: (r["employeeName"], r["date"]))
    current_emp = None
    emp_hours = 0.0
    emp_missing = emp_unjustified = 0

    def pad(row):
        return row + [""] * (COLS - len(row))

    def flush_subtotal():
        if current_emp is not None:
            just_summary = f"{emp_unjustified} injustificada(s)" if emp_unjustified else ""
            w.writerow(pad([
                f"Subtotal {current_emp}", "", "", "", "", "", "", "",
                f"{emp_hours:.2f}", "", "",
                f"{emp_missing}" if emp_missing else "",
                just_summary,
            ]))
            w.writerow([])

    for r in sorted_rows:
        if current_emp is not None and r["employeeName"] != current_emp:
            flush_subtotal()
            emp_hours = 0.0
            emp_missing = emp_unjustified = 0
        current_emp = r["employeeName"]
        emp_hours += r["hours"]
        if r["missing"]:
            emp_missing += 1
        if r.get("justified") is False:
            emp_unjustified += 1

        fecha_dt = datetime.strptime(r["date"], "%Y-%m-%d")
        cat = CATEGORY_LABELS.get(categories.get(r["employeeId"]), "")

        justificante = ""
        if r.get("justified") is True:
            justificante = f"Sí — {r.get('justificationType') or ''}".rstrip(" —")
        elif r.get("justified") is False:
            justificante = "No"

        w.writerow([
            r["employeeName"], cat, fecha_dt.strftime("%d/%m/%Y"), dow_names[fecha_dt.weekday()],
            r["entrada"] or "—", r["comida_salida"] or "—", r["comida_entrada"] or "—", r["salida"] or "—",
            f"{r['hours']:.2f}",
            r["retardoMin"] or "", r["lunchLateMin"] or "",
            "Sí" if r["missing"] else "",
            justificante,
        ])
    flush_subtotal()

    total_hours = sum(r["hours"] for r in all_rows)
    total_missing = sum(1 for r in all_rows if r["missing"])
    total_unjustified = sum(1 for r in all_rows if r.get("justified") is False)
    total_just_summary = f"{total_unjustified} injustificada(s)" if total_unjustified else ""
    w.writerow(pad([
        "TOTAL GENERAL", "", "", "", "", "", "", "",
        f"{total_hours:.2f}", "", "",
        f"{total_missing}" if total_missing else "",
        total_just_summary,
    ]))

    return ("﻿" + buf.getvalue()).encode("utf-8")
