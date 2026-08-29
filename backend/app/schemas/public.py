from pydantic import BaseModel


class VerifyPinRequest(BaseModel):
    pin: str = ""


class PunchRequest(BaseModel):
    employeeId: str = ""
    employeeName: str = ""
    type: str = ""
