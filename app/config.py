"""Configuração em .env; credenciais não entram nos schemas públicos."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 256 * 1024
MAX_DOCX_BYTES = 50 * 1024 * 1024
MAX_DOCX_ENTRIES = 2000
ALLOWED_EXTENSIONS = frozenset({".pdf", ".docx"})

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///.data/app.db"
    data_dir: Path = Path(".data")
    api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-flash"
    jev_api_key: str = ""
    jev_model: str = "jev-1.13"

settings = Settings()
