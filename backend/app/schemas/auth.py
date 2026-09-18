from typing import List, Optional

from pydantic import BaseModel


class ConfigUpdate(BaseModel):
    password: Optional[str] = None
    lunchMinutes: Optional[str] = None
    generateRecovery: Optional[bool] = None
    officialEmail: Optional[str] = None


class LoginRequest(BaseModel):
    password: str = ""


class RecoverRequest(BaseModel):
    recoveryCode: str = ""
    newPassword: str = ""


class SecurityQuestionItem(BaseModel):
    question: str
    answer: str


class SecurityQuestionsUpdate(BaseModel):
    questions: List[SecurityQuestionItem] = []


class SecurityRecoverRequest(BaseModel):
    answers: List[str] = []
    newPassword: str = ""


class SecurityAnswersVerify(BaseModel):
    answers: List[str] = []
