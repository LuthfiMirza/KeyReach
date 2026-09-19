"""
core/logger.py — Centralised logging configuration
===================================================
* All logs go to  app.log  (rotating, max 5 MB × 3 backups)
* stdout / stderr remain CLEAN — only structured JSON or Markdown is printed,
  so AI Agents receive uncontaminated output.
* Call get_logger(__name__) in every module.
"""

from __future__ import annotations

import logging
import logging.handlers
import os

LOG_FILE = os.environ.get("KEYREACH_LOG_FILE", "app.log")
LOG_LEVEL = os.environ.get("KEYREACH_LOG_LEVEL", "DEBUG").upper()

_configured = False


def _configure_once() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger("keyreach")
    root.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    # ── Rotating file handler ──────────────────────────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root.addHandler(fh)

    # ── NO stdout/stderr handler ── (keep AI output clean) ────────────────
    # If you need console output during development, uncomment:
    # sh = logging.StreamHandler()
    # sh.setLevel(logging.WARNING)
    # root.addHandler(sh)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger namespaced under 'keyreach.<name>'.

    All output is routed to app.log only.
    """
    _configure_once()
    # Strip leading __main__ if present
    suffix = name.replace("__main__", "main")
    return logging.getLogger(f"keyreach.{suffix}")
