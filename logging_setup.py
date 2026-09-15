import logging
from logging.handlers import RotatingFileHandler
from config import settings


def setup_logging():
    settings.ensure_dirs()
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        settings.logs_dir / "monitor.log",
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
