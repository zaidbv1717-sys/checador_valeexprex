from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .. import crud, mailer, rate_limit, schemas, security
from ..config import settings
from ..database import get_db
from ..deps import require_admin
from ..net import client_ip

router = APIRouter(prefix="/admin", tags=["admin-auth"])


def _normalize_answer(answer: str) -> str:
    # Mismo criterio en guardado y verificacion: sin esto "Guadalajara" y
    # "guadalajara " se tratarian como respuestas distintas.
    return answer.strip().lower()


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


@router.post("/recover/resend-code")
def resend_recovery_code(request: Request, db: Session = Depends(get_db)):
    # Publico a proposito: es justo para quien no puede iniciar sesion y el
    # correo original no llego (p. ej. el SMTP no estaba configurado todavia).
    # No revela el codigo aqui: solo dispara el mismo envio que ya hace
    # generateRecovery, al correo oficial ya guardado.
    key = f"recover-resend:{client_ip(request)}"
    if rate_limit.is_locked(key):
        return JSONResponse(
            {"ok": False, "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )
    rate_limit.register_failure(key)

    cfg = crud.get_config(db)
    code = cfg.get("recovery_code", "")
    official_email = cfg.get("official_email", "").strip()
    if not code:
        return JSONResponse({"ok": False, "error": "No hay código de recuperación generado"}, status_code=400)
    if not official_email:
        return JSONResponse({"ok": False, "error": "No hay correo oficial configurado en Ajustes"}, status_code=400)

    try:
        mailer.send_email(
            official_email,
            "Código de recuperación - Reloj Checador",
            f"Tu código de recuperación para restablecer la contraseña de administrador es:\n\n{code}\n\n"
            "Si no lo solicitaste, cambia la contraseña de administrador cuanto antes.",
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    return {"ok": True}


@router.get("/security-questions")
def get_security_questions(db: Session = Depends(get_db)):
    # Publico a proposito: quien perdio la contrasena necesita ver las
    # preguntas antes de iniciar sesion. Las respuestas nunca se exponen aqui.
    questions = crud.get_security_questions(db)
    return {"questions": [q["question"] for q in questions]}


@router.post("/security-questions", dependencies=[Depends(require_admin)])
def set_security_questions(body: schemas.SecurityQuestionsUpdate, db: Session = Depends(get_db)):
    cleaned = [
        {"question": q.question.strip(), "answerHash": security.hash_password(_normalize_answer(q.answer))}
        for q in body.questions
        if q.question.strip() and q.answer.strip()
    ]
    if len(cleaned) < 3:
        return JSONResponse(
            {"ok": False, "error": "Configura al menos 3 preguntas, todas con pregunta y respuesta"},
            status_code=400,
        )
    crud.set_security_questions(db, cleaned)
    return {"ok": True}


@router.post("/recover-security")
def recover_security(request: Request, body: schemas.SecurityRecoverRequest, db: Session = Depends(get_db)):
    key = f"recover-security:{client_ip(request)}"
    if rate_limit.is_locked(key):
        return JSONResponse(
            {"ok": False, "error": "Demasiados intentos. Espera unos minutos."},
            status_code=429,
        )

    questions = crud.get_security_questions(db)
    if not questions:
        return JSONResponse({"ok": False, "error": "No hay preguntas de seguridad configuradas"}, status_code=400)
    if len(body.answers) != len(questions):
        rate_limit.register_failure(key)
        return JSONResponse({"ok": False, "error": "Respuestas incompletas"}, status_code=400)

    all_correct = all(
        security.verify_password(_normalize_answer(given), q["answerHash"])
        for given, q in zip(body.answers, questions)
    )
    if not all_correct:
        rate_limit.register_failure(key)
        return JSONResponse({"ok": False, "error": "Una o más respuestas son incorrectas"}, status_code=400)

    new_pass = body.newPassword.strip()
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
