from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud, mailer, rate_limit, schemas, security
from ..config import settings
from ..database import get_db
from ..deps import require_admin
from ..net import client_ip

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/login")
def login(request: Request, body: schemas.LoginRequest, db: Session = Depends(get_db)):
    # Sin freno, una contrasena de 4 caracteres se agota en minutos.
    key = f"login:{client_ip(request)}"
    if rate_limit.is_locked(key):
        return JSONResponse(
            {"ok": False, "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )

    cfg = crud.get_config(db)
    stored_hash = cfg.get("password")
    if stored_hash is None:
        ok = body.password == settings.default_admin_password
    else:
        ok = security.verify_password(body.password, stored_hash)
    if not ok:
        rate_limit.register_failure(key)
        # 401, no 200: un 200 con {"ok": false} impide que nginx o cualquier
        # herramienta de monitoreo cuente los fallos de autenticacion.
        return JSONResponse({"ok": False, "error": "Contraseña incorrecta"}, status_code=401)

    rate_limit.reset(key)
    # Comparar contra el hash almacenado, no contra `stored_hash is None`: el
    # arranque siembra el hash siempre, asi que aquella condicion era siempre
    # falsa y el aviso de "sigues usando la contrasena por defecto" nunca salia.
    using_default = security.verify_password(settings.default_admin_password, stored_hash) \
        if stored_hash else True
    return {"ok": True, "usingDefaultPassword": using_default}


@router.post("/recover")
def recover(request: Request, body: schemas.RecoverRequest, db: Session = Depends(get_db)):
    key = f"recover:{client_ip(request)}"
    if rate_limit.is_locked(key):
        return JSONResponse(
            {"ok": False, "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )

    cfg = crud.get_config(db)
    code = body.recoveryCode.strip().upper()
    new_pass = body.newPassword.strip()
    if code != cfg.get("recovery_code", ""):
        rate_limit.register_failure(key)
        return JSONResponse({"ok": False, "error": "Código de recuperación incorrecto"}, status_code=400)
    if len(new_pass) < 4:
        return JSONResponse({"ok": False, "error": "La nueva contraseña debe tener al menos 4 caracteres"}, status_code=400)
    rate_limit.reset(key)
    crud.set_config(db, {"password": security.hash_password(new_pass)})
    return {"ok": True}


@router.get("/config", dependencies=[Depends(require_admin)])
def get_config_route(db: Session = Depends(get_db)):
    cfg = crud.get_config(db)
    # El codigo de recuperacion no se devuelve aqui: sirve para restablecer la
    # contrasena, asi que exponerlo a quien ya inicio sesion anula su proposito.
    # Solo se muestra al generarlo (POST /config con generateRecovery).
    return {
        "lunchMinutes": cfg.get("lunch_minutes", "90"),
        "hasRecoveryCode": bool(cfg.get("recovery_code")),
        "officialEmail": cfg.get("official_email", ""),
    }


@router.post("/config", dependencies=[Depends(require_admin)])
def update_config(body: schemas.ConfigUpdate, db: Session = Depends(get_db)):
    partial = {}
    if body.password:
        partial["password"] = security.hash_password(body.password)
    if body.lunchMinutes:
        partial["lunch_minutes"] = body.lunchMinutes
    if body.officialEmail is not None:
        partial["official_email"] = body.officialEmail.strip()
    if body.generateRecovery:
        partial["recovery_code"] = crud.gen_recovery_code()
    crud.set_config(db, partial)
    cfg = crud.get_config(db)

    # Ademas de mostrarse una sola vez en pantalla, el codigo nuevo se manda al
    # correo oficial si esta configurado: es la unica forma de recuperarlo si se
    # pierde la nota. Un fallo de envio no debe tirar la generacion del codigo.
    email_error = None
    if body.generateRecovery:
        official_email = cfg.get("official_email", "").strip()
        if official_email:
            try:
                mailer.send_email(
                    official_email,
                    "Código de recuperación - Reloj Checador",
                    "Se generó un nuevo código de recuperación para restablecer la "
                    f"contraseña de administrador:\n\n{cfg.get('recovery_code', '')}\n\n"
                    "Guárdalo en un lugar seguro; no se volverá a mostrar. Si no "
                    "solicitaste este código, cambia la contraseña de administrador.",
                )
            except Exception as exc:
                email_error = str(exc)

    # Solo se revela el codigo recien generado, en la unica respuesta que lo trae.
    return {
        "ok": True,
        "recoveryCode": cfg.get("recovery_code", "") if body.generateRecovery else None,
        "emailError": email_error,
    }
