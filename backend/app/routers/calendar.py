from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import reports
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["calendar"], dependencies=[Depends(require_admin)])


@router.get("/calendar")
def get_calendar(
    employeeId: str = "",
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
):
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    if not employeeId:
        return {"days": []}
    days = reports.compute_calendar(db, employeeId, year, month)
    return {"days": days}
