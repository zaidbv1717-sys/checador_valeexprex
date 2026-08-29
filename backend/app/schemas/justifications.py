from typing import Optional

from pydantic import BaseModel


class JustificationCreate(BaseModel):
    employeeId: str = ""
    employeeName: str = ""
    dateStart: str = ""
    dateEnd: Optional[str] = None
    type: str = ""
    status: str = "aprobada"
    note: Optional[str] = ""


class JustificationStatusUpdate(BaseModel):
    id: str = ""
    status: str = ""
