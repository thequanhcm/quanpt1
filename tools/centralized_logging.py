"""Centralized logging setup for QUAN AI BRAIN.

Creates log rotation, aggregation, and monitoring.
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
LOGS_DIR = WORKSPACE / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup centralized logger with rotation."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Log file path
    log_file = LOGS_DIR / f"{name}.log"
    
    # Rotating file handler (5 files, 10MB each)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


# Pre-create loggers for all components
server_logger = setup_logger("server")
watchdog_logger = setup_logger("watchdog")
learning_logger = setup_logger("learning")
responder_logger = setup_logger("responder")
dashboard_logger = setup_logger("dashboard")
audit_logger = setup_logger("audit")


def log_audit(action: str, data: dict):
    """Log audit event."""
    import json
    audit_logger.info(f"AUDIT | {action} | {json.dumps(data, ensure_ascii=False)}")


if __name__ == "__main__":
    # Test logging
    test_logger = setup_logger("test")
    test_logger.info("Test log message")
    test_logger.warning("Test warning")
    test_logger.error("Test error")
    
    print(f"\n✅ Loggers created in: {LOGS_DIR}")
    print("Files:")
    for f in LOGS_DIR.glob("*.log"):
        print(f"  - {f.name}")