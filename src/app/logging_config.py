"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from typing import Optional

from .config import settings


def setup_logging(
    log_dir: str = "logs",
    log_level: Optional[str] = None,
    enable_console: bool = True,
) -> None:
    """
    Configure application-wide logging.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: Whether to also log to console
    """
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Determine log level
    level = getattr(logging, (log_level or settings.debug and "DEBUG" or "INFO"))

    # Create formatter
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d | %(levelname)-8s | "
            "%(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # File handler for all logs (with rotation could be added)
    file_handler = logging.FileHandler(
        log_path / "app.log",
        mode="a",
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Separate file for LLM interactions only
    llm_handler = logging.FileHandler(
        log_path / "llm.log",
        mode="a",
        encoding="utf-8",
    )
    llm_handler.setLevel(level)
    llm_handler.setFormatter(detailed_formatter)

    # Filter to only capture LLM-related logs
    class LLMFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return record.name.startswith("app.chat.llm") or "llm" in record.name

    llm_handler.addFilter(LLMFilter())
    root_logger.addHandler(llm_handler)

    # Console handler (optional)
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

    # Log startup message
    logging.info(f"Logging initialized: level={logging.getLevelName(level)}, dir={log_dir}")


def get_llm_logger(name: str = "app.chat.llm") -> logging.Logger:
    """Get a logger specifically for LLM operations."""
    return logging.getLogger(name)


# Convenience log functions for direct use
def log_llm_request(
    method: str,
    messages_count: int,
    model: str,
    temperature: float,
    is_fallback: bool = False,
    **kwargs,
) -> None:
    """Log an outgoing LLM request."""
    logger = get_llm_logger()
    fallback_tag = " [FALLBACK]" if is_fallback else ""
    logger.info(
        f"Request → {method}{fallback_tag} | model={model} | temp={temperature} | "
        f"messages={messages_count} | kwargs={kwargs}"
    )


def log_llm_response(
    method: str,
    status: str,
    content_length: int,
    usage: Optional[dict] = None,
    model: Optional[str] = None,
    duration_ms: Optional[float] = None,
    is_fallback: bool = False,
) -> None:
    """Log an incoming LLM response."""
    logger = get_llm_logger()
    fallback_tag = " [FALLBACK]" if is_fallback else ""
    usage_str = f" | usage={usage}" if usage else ""
    model_str = f" | model={model}" if model else ""
    duration_str = f" | {duration_ms:.1f}ms" if duration_ms else ""
    logger.info(
        f"Response ← {method}{fallback_tag} | status={status} | len={content_length}"
        f"{model_str}{usage_str}{duration_str}"
    )


def log_llm_error(
    method: str,
    error: Exception,
    context: Optional[dict] = None,
) -> None:
    """Log an LLM-related error."""
    logger = get_llm_logger()
    context_str = f" | context={context}" if context else ""
    logger.error(
        f"Error in {method}: {type(error).__name__}: {error}{context_str}",
        exc_info=True,
    )


if __name__ == "__main__":
    # Quick test
    setup_logging(log_level="DEBUG")
    logging.getLogger("app.chat.llm").debug("Test LLM log")
    logging.getLogger("app.chat.llm").info("Test info message")
    print("Logging setup complete. Check logs/app.log and logs/llm.log")
