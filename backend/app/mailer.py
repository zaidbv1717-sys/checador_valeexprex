import smtplib
from email.mime.text import MIMEText

from .config import settings


class MailerNotConfigured(Exception):
    pass


def send_email(to_addr: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        raise MailerNotConfigured(
            "El correo oficial esta configurado pero el servidor SMTP no "
            "(faltan SMTP_HOST / SMTP_USER / SMTP_PASSWORD)."
        )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to_addr

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(msg["From"], [to_addr], msg.as_string())
