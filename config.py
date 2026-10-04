import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    erp_host: str = "127.0.0.1"
    erp_port: int = 8000
    approval_threshold: float = 10000.0
    max_retries: int = 3
    log_dir: str = "logs"
    database_path: str = "erp_data.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def erp_base_url(self) -> str:
        port_env = os.environ.get("PORT")
        effective_port = int(port_env) if port_env else self.erp_port
        return f"http://127.0.0.1:{effective_port}"

    @property
    def log_path(self) -> Path:
        p = Path(self.log_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
