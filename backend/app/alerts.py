from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import crud, models
from .config import settings


def check_device_alert(db: Session, ip, employee_id, employee_name, ts):
    """Detección silenciosa: si otro empleado distinto marcó 'entrada' desde la
    misma IP hace pocos minutos, registra una alerta para el administrador."""
    if not ip:
        return
    window_start = ts - timedelta(minutes=settings.device_alert_window_min)
    recent = db.query(models.Record).filter(
        models.Record.type == "entrada",
        models.Record.source_ip == ip,
        models.Record.employee_id != employee_id,
        models.Record.timestamp >= window_start,
    ).order_by(models.Record.timestamp.desc()).first()
    if recent:
        db.add(models.DeviceAlert(
            id=crud.uid(), ip=ip, emp1_name=recent.employee_name, emp1_time=recent.timestamp,
            emp2_name=employee_name, emp2_time=ts, created_at=datetime.now(), resolved=0,
        ))
        db.commit()
