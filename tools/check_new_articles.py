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

