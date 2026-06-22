"""Entry point: ``python -m llm_server``.

Reads ``Settings`` (which loads ``~/.heartbox-llm.env``), builds the FastAPI
app, and hands it to uvicorn.
"""
import logging

import uvicorn

from .config import Settings
from .main import create_app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    settings = Settings()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level='info',
        access_log=False,  # PII — request bodies could contain journal text
    )


if __name__ == '__main__':
    main()
