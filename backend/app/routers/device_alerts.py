from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["device-alerts"], dependencies=[Depends(require_admin)])


@router.get("/device-alerts")
def list_device_alerts(db: Session = Depends(get_db)):
    alerts = db.query(models.DeviceAlert).filter(models.DeviceAlert.resolved == 0).order_by(
        models.DeviceAlert.created_at.desc()
    ).limit(20).all()
    return {"alerts": [
        {
            "id": a.id, "ip": a.ip, "emp1_name": a.emp1_name,
            "emp1_time": a.emp1_time.isoformat() if a.emp1_time else None,
            "emp2_name": a.emp2_name,
            "emp2_time": a.emp2_time.isoformat() if a.emp2_time else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "resolved": a.resolved,
        }
        for a in alerts
    ]}


@router.post("/device-alerts/resolve")
def resolve_device_alert(body: schemas.ResolveAlertRequest, db: Session = Depends(get_db)):
    alert = db.get(models.DeviceAlert, body.id)
    if alert:
        alert.resolved = 1
        db.commit()
    return {"ok": True}
