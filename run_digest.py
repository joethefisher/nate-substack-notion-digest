#!/usr/bin/env python3
"""
Nate's Newsletter Substack Digest
Scrapes new articles from natesnewsletter.substack.com,
summarizes each with Claude, and creates Notion pages.

Usage:
    python3 run_digest.py              # normal run
    python3 run_digest.py --dry-run    # scrape + summarize but skip Notion writes
    python3 run_digest.py --verbose    # extra logging
"""

import argparse
import fcntl
import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
TMP_DIR = PROJECT_ROOT / ".tmp"
ENV_FILE = PROJECT_ROOT / ".env"
LOG_FILE = TMP_DIR / "digest.log"
LOCK_FILE = TMP_DIR / "digest.lock"

load_dotenv(ENV_FILE)

SUBSTACK_URL = "https://natesnewsletter.substack.com/"


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE),
        ],
    )


def ensure_runtime_dirs() -> None:
    TMP_DIR.mkdir(exist_ok=True)


@contextmanager
def acquire_run_lock():
    with open(LOCK_FILE, "w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another digest run is already in progress.") from exc
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def validate_env(require_notion: bool) -> tuple[str, str | None, str | None]:
    """
    Check required env vars are present. Returns (anthropic_key, notion_key, db_id).
    Raises EnvironmentError listing missing vars.
    """
    required = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }
    if require_notion:
        required["NOTION_API_KEY"] = os.getenv("NOTION_API_KEY")
        required["NOTION_DATABASE_ID"] = os.getenv("NOTION_DATABASE_ID")

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please add them to your .env file."
        )
    return (
        required["ANTHROPIC_API_KEY"],
        required.get("NOTION_API_KEY"),
        required.get("NOTION_DATABASE_ID"),
    )

