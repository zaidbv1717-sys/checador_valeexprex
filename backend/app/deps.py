from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import crud, security
from .config import settings
from .database import get_db


def require_admin(x_admin_pass: str = Header(default=""), db: Session = Depends(get_db)) -> None:
    cfg = crud.get_config(db)
    stored_hash = cfg.get("password")
    if stored_hash is None:
        ok = x_admin_pass == settings.default_admin_password
    else:
        ok = security.verify_password(x_admin_pass, stored_hash)
    if not ok:
        raise HTTPException(status_code=401, detail="unauthorized")
