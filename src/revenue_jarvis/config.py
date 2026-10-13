"""Typed settings. Override any field with an env var JARVIS_<NAME> or a .env file."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _default_data_dir() -> Path:
    """Project checkout's data/ (editable install), else ./data in the current folder."""
    here = PACKAGE_ROOT / "data"
    return here if here.exists() else Path.cwd() / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JARVIS_", env_file=".env", extra="ignore")

    data_dir: Path = Field(default_factory=_default_data_dir)
    db_name: str = "jarvis.db"
    # Your own copy of the book PDF. Used only to show original page images; never uploaded anywhere.
    book_pdf: Path | None = None

    embed_model: str = "intfloat/multilingual-e5-small"
    embed_revision: str = "main"

    rrf_k: int = 60
    candidate_depth: int = 30
    top_book: int = 5          # primary evidence: the Bhumbak book
    top_law: int = 3           # secondary evidence: bare acts / rules / manuals

    # Thinking engine. "auto" tries Claude Code, then Codex, then sources-only. No API keys.
    llm_backend: Literal["auto", "claude", "codex", "none"] = "auto"
    claude_model: str | None = None          # e.g. "sonnet"; None = your Claude Code default
    llm_timeout_s: int = 150
    llm_query_rewrite: bool = False          # opt in only after measuring rewrite quality/latency

    # Voice
    stt_engine: Literal["mlx", "faster-whisper", "browser"] = "mlx"
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"

    user_title: str = "sir"
    host: str = "127.0.0.1"
    port: int = 8765

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_name


def get_settings() -> Settings:
    return Settings()
