"""Settings for the FastAPI inference server.

Reads ``%USERPROFILE%\\.heartbox-llm.env`` first, then process env vars.
``API_KEY`` is required — server refuses to start if missing.
"""
from __future__ import annotations

import os
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _HAS_PYDANTIC_SETTINGS = True
except ImportError:  # pragma: no cover
    _HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = dict  # type: ignore


_DEFAULT_ENV_FILE = Path(os.environ.get('USERPROFILE', str(Path.home()))) / '.heartbox-llm.env'


class Settings(BaseSettings):
    """Required + optional knobs for the inference server."""

    if _HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=str(_DEFAULT_ENV_FILE),
            env_file_encoding='utf-8',
            extra='ignore',
        )

    # --- Auth ----------------------------------------------------------
    api_key: str = ''  # REQUIRED in practice — validated in main()

    # --- Network -------------------------------------------------------
    host: str = '127.0.0.1'
    port: int = 8765
    cors_allow_origins: str = ''   # comma-separated, no wildcards
    body_limit_bytes: int = 100_000
    request_timeout_s: int = 60

    # --- Models --------------------------------------------------------
    taide_model_id: str = 'taide/TAIDE-LX-7B-Chat'
    llava_model_id: str = 'llava-hf/llava-v1.6-mistral-7b-hf'
    bnb_disable: bool = False                  # set True for tiny models in dev
    max_context_tokens: int = 8192
    sticky_vision: bool = False                # if True, don't auto-swap back
    autoload_on_startup: bool = True           # load TAIDE in lifespan

    # --- Logging -------------------------------------------------------
    log_prompts: bool = False                  # opt-in PII for debugging only

    # --- HuggingFace cache --------------------------------------------
    hf_home: str = ''                          # if set, exported before any HF import

    # ------------------------------------------------------------------
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(',') if o.strip()]
