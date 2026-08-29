from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud, schemas, security
from ..config import settings
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login")
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    cfg = crud.get_config(db)
    stored_hash = cfg.get("password")
    if stored_hash is None:
        ok = body.password == settings.default_admin_password
    else:
        ok = security.verify_password(body.password, stored_hash)
    return {"ok": ok}


@router.post("/recover")
def recover(body: schemas.RecoverRequest, db: Session = Depends(get_db)):
    cfg = crud.get_config(db)
    code = body.recoveryCode.strip().upper()
    new_pass = body.newPassword.strip()
    if code != cfg.get("recovery_code", ""):
        return JSONResponse({"ok": False, "error": "Código de recuperación incorrecto"}, status_code=400)
    if len(new_pass) < 4:
        return JSONResponse({"ok": False, "error": "La nueva contraseña debe tener al menos 4 caracteres"}, status_code=400)
    crud.set_config(db, {"password": security.hash_password(new_pass)})
    return {"ok": True}


@router.get("/config", dependencies=[Depends(require_admin)])
def get_config_route(db: Session = Depends(get_db)):
    cfg = crud.get_config(db)
    return {"lunchMinutes": cfg.get("lunch_minutes", "90"), "recoveryCode": cfg.get("recovery_code", "")}


@router.post("/config", dependencies=[Depends(require_admin)])
def update_config(body: schemas.ConfigUpdate, db: Session = Depends(get_db)):
    partial = {}
    if body.password:
        partial["password"] = security.hash_password(body.password)
    if body.lunchMinutes:
        partial["lunch_minutes"] = body.lunchMinutes
    if body.generateRecovery:
        partial["recovery_code"] = crud.gen_recovery_code()
    crud.set_config(db, partial)
    cfg = crud.get_config(db)
    return {"ok": True, "recoveryCode": cfg.get("recovery_code", "")}
