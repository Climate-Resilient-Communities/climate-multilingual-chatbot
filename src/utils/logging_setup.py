import logging
import os
from logging.handlers import RotatingFileHandler


def ensure_file_logger(
    log_file_path: str,
    level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> str:
    """Attach a rotating UTF-8 file handler to the root logger once.

    Returns the absolute path to the configured log file.
    """
    if not log_file_path:
        log_file_path = os.path.join(os.getcwd(), "logs", "pipeline_debug.log")

    abs_path = os.path.abspath(log_file_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    root_logger = logging.getLogger()

    # Check if a handler for this exact path already exists
    for h in root_logger.handlers:
        if isinstance(h, (RotatingFileHandler, logging.FileHandler)):
            try:
                if os.path.abspath(getattr(h, 'baseFilename', '')) == abs_path:
                    return abs_path
            except Exception:
                continue

    # Respect production default: only enable when explicitly opted-in
    if str(os.environ.get("ENABLE_LOCAL_CHAT_LOGS", "")).strip().lower() in ("1", "true", "yes"):
        file_handler = RotatingFileHandler(
            abs_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)

        root_logger.addHandler(file_handler)
        if root_logger.level > level:
            root_logger.setLevel(level)

    # Make noisy libs inherit and go to file
    for noisy in ("httpx", "urllib3"):
        try:
            nl = logging.getLogger(noisy)
            nl.setLevel(logging.INFO)
            nl.propagate = True
        except Exception:
            pass

    return abs_path


