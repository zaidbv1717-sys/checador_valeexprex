from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = "postgresql://reloj:reloj@localhost:5432/reloj_checador"
    port: int = 8000
    max_backups: int = 30
    device_alert_window_min: int = 5
    default_admin_password: str = "1234"
    # Zona horaria de la oficina. Mazatlan es MST (-0700) y NO comparte hora con
    # Ciudad de Mexico (CST, -0600); ver app/clock.py.
    office_tz: str = "America/Mazatlan"
    backup_dir: str = str(REPO_ROOT / "data" / "backups")
    photos_dir: str = str(REPO_ROOT / "data" / "photos")
    punch_photos_dir: str = str(REPO_ROOT / "data" / "punch_photos")
    # Tope de subida de fotos. Una camara de celular ronda 2-5 MB.
    max_photo_bytes: int = 8 * 1024 * 1024

    # --- Ajustes que solo importan fuera de la LAN de la oficina -------------
    # En la PC de la oficina el checador vive en una WiFi de confianza y estos
    # defaults abiertos son comodos. En un servidor alcanzable desde internet
    # (staging) los dos se cierran por .env; ver .env.staging.example.

    # `/docs` publica el mapa completo de la API, incluidos los endpoints de
    # admin. Util al desarrollar, regalo para quien busque por donde entrar.
    docs_enabled: bool = True

    # Origenes permitidos por CORS, separados por coma. "*" es el default
    # historico (LAN); en internet se acota al dominio real del checador.
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        """`cors_origins` como lista. Una cadena vacia equivale a no permitir
        ningun origen cruzado, que es lo correcto cuando el frontend se sirve
        desde el mismo dominio que la API."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
