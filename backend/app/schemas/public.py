from pydantic import BaseModel


class VerifyPinRequest(BaseModel):
    pin: str = ""
