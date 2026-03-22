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


def save_processed_state(state: dict, state_file: str | Path = STATE_FILE) -> None:
    """
    Atomically write state to disk using a temp file + rename.
    This prevents corruption if the process crashes mid-write.
    """
    state_path = Path(state_file)
    os.makedirs(state_path.parent, exist_ok=True)
    dir_name = os.path.dirname(os.path.abspath(state_path))
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_name, delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(state, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, state_path)


def filter_new_articles(articles: list, state: dict) -> list:
    """
    Return only articles whose URL is not in the processed state.
    Pure function — no side effects.
    """
    processed = set(state.get("processed_urls", []))
    return [a for a in articles if a["url"] not in processed]


def mark_article_processed(url: str, state: dict) -> dict:
    """
    Return an updated state dict with the URL added to processed_urls.
    Pure function — caller is responsible for calling save_processed_state.
    """
    updated = dict(state)
    processed = list(state.get("processed_urls", []))
    if url not in processed:
        processed.append(url)
    updated["processed_urls"] = processed
    updated["last_run"] = datetime.now(timezone.utc).isoformat()
    updated["article_count"] = len(processed)
    return updated
