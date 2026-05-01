from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL_NAME = "gemma3:4b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LYW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default=Path("./data"))
    db_path: Path = Field(default=Path("./data/lyw.db"))
    qdrant_url: str = Field(default="http://localhost:6333")
    redis_url: str = Field(default="redis://localhost:6379/0")
    ollama_base_url: str = Field(default="http://localhost:11434")
    model_name: str = Field(default=DEFAULT_MODEL_NAME)
    log_format: Literal["console", "json"] = Field(default="console")
    docling_device: Literal["auto", "cpu", "cuda", "mps", "xpu"] = Field(default="auto")
