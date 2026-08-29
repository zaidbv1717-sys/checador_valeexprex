import random
import string
import uuid

from sqlalchemy.orm import Session

from . import models


def uid() -> str:
    return uuid.uuid4().hex[:12]


def gen_recovery_code() -> str:
    return '-'.join(
        ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        for _ in range(2)
    )


def get_config(db: Session) -> dict:
    rows = db.query(models.ConfigEntry).all()
    return {r.key: r.value for r in rows}


def set_config(db: Session, partial: dict) -> None:
    for k, v in partial.items():
        entry = db.get(models.ConfigEntry, k)
        if entry:
            entry.value = str(v)
        else:
            db.add(models.ConfigEntry(key=k, value=str(v)))
    db.commit()
