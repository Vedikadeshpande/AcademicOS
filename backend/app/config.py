"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./academic_os.db"
    UPLOAD_DIR: str = "./uploads"
    VECTOR_STORE_DIR: str = "./vector_store"
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = "llama-3.3-70b-versatile" 
    SECRET_KEY: str = "academic-os-dev-secret-key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_dirs(self):
        """Create required directories if they don't exist."""
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.VECTOR_STORE_DIR).mkdir(parents=True, exist_ok=True)


settings = Settings()
