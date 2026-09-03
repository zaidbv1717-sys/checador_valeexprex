from datetime import datetime, timedelta

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

PUNCH_TYPE_LABELS = {
    "entrada": "Entrada",
    "comida_salida": "Salida a comer",
    "comida_entrada": "Regreso de comer",
    "salida": "Salida",
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
