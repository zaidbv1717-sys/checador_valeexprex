from typing import Optional

from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    name: str = ""
    pin: str = ""
    category: str = "trabajador"
    schedIn: Optional[str] = None
    schedOut: Optional[str] = None
    lunchMinutes: Optional[str] = None
