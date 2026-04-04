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


