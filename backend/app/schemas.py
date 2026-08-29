from typing import Optional

from pydantic import BaseModel


class VerifyPinRequest(BaseModel):
    pin: str = ""


class PunchRequest(BaseModel):
    employeeId: str = ""
    employeeName: str = ""
    type: str = ""


class EmployeeCreate(BaseModel):
    name: str = ""
    pin: str = ""
    category: str = "trabajador"
    schedIn: Optional[str] = None
    schedOut: Optional[str] = None
    lunchMinutes: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    id: str = ""


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


class ManualEditRequest(BaseModel):
    employeeId: str = ""
    employeeName: str = ""
    dateStr: str = ""
    edits: dict[str, Optional[str]] = {}
    note: Optional[str] = None


class ConfigUpdate(BaseModel):
    password: Optional[str] = None
    lunchMinutes: Optional[str] = None
    generateRecovery: Optional[bool] = None


class LoginRequest(BaseModel):
    password: str = ""


class RecoverRequest(BaseModel):
    recoveryCode: str = ""
    newPassword: str = ""
