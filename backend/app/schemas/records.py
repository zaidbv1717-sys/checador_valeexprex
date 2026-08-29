from typing import Optional

from pydantic import BaseModel


class ManualEditRequest(BaseModel):
    employeeId: str = ""
    employeeName: str = ""
    dateStr: str = ""
    edits: dict[str, Optional[str]] = {}
    note: Optional[str] = None
