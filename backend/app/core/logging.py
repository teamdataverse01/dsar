import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    level = logging.DEBUG if settings.is_dev else logging.INFO
    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        if settings.is_dev
        else '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    )
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
