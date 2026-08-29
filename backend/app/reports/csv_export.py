import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session

from .. import models
from .common import CATEGORY_LABELS


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
