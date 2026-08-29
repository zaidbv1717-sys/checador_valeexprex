from pydantic import BaseModel


class ResolveAlertRequest(BaseModel):
    id: str = ""
