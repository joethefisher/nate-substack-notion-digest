"""
State management for processed articles.
Tracks which Substack article URLs have already been processed
to prevent duplicate Notion pages.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PROJECT_ROOT / ".tmp" / "processed_articles.json"


def load_processed_state(state_file: str | Path = STATE_FILE) -> dict:
    """
    Load the processed articles state from disk.
    Returns a fresh state dict if the file is missing or corrupted.
    """
    state_path = Path(state_file)
    try:
        with state_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if "processed_urls" not in data:
                raise ValueError("Invalid state file structure")
            return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return {
            "processed_urls": [],
            "last_run": None,
            "article_count": 0,
        }
