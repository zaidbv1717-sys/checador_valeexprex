from typing import Optional

from pydantic import BaseModel


class ConfigUpdate(BaseModel):
    password: Optional[str] = None
    lunchMinutes: Optional[str] = None
    generateRecovery: Optional[bool] = None


class LoginRequest(BaseModel):
    password: str = ""


class RecoverRequest(BaseModel):
    recoveryCode: str = ""
    newPassword: str = ""
