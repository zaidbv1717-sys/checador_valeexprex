from datetime import date
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Tipos de marca validos. Usar Literal en vez de `str` hace que Pydantic rechace
# lo invalido en el borde con un 422, en vez de dejarlo llegar a la base de datos.
PunchType = Literal["entrada", "comida_salida", "comida_entrada", "salida"]

# "HH:MM" de 24 horas. Antes un "99:99" llegaba a datetime.replace() y reventaba
# con un 500.
HourMinute = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class ManualEditRequest(BaseModel):
    employeeId: str = Field(min_length=1)
    employeeName: str = ""
    # `date` en vez de str: Pydantic rechaza "no-es-fecha" antes de llegar a strptime.
    dateStr: date
    edits: dict[PunchType, Optional[HourMinute]] = {}
    note: Optional[str] = None

    @field_validator("edits")
    @classmethod
    def drop_empty(cls, v: dict) -> dict:
        # La UI manda "" para los campos que el admin dejo vacios.
        return {k: val for k, val in v.items() if val}
