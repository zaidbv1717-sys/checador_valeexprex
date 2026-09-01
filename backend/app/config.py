from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = "postgresql://reloj:reloj@localhost:5432/reloj_checador"
    port: int = 8000
    max_backups: int = 30
    device_alert_window_min: int = 5
    default_admin_password: str = "1234"
    backup_dir: str = str(REPO_ROOT / "data" / "backups")
    photos_dir: str = str(REPO_ROOT / "data" / "photos")
    punch_photos_dir: str = str(REPO_ROOT / "data" / "punch_photos")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
