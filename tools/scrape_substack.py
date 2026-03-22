"""
Scrape the Nate's Newsletter Substack index page and return a list of article dicts.
Uses the Firecrawl CLI (already installed and authenticated) via subprocess.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from urllib.parse import urljoin, urlparse

FIRECRAWL_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 1.0


def normalize_domain(domain: str) -> str:
    return domain.lower().removeprefix("www.")


def is_allowed_article_url(candidate_url: str, substack_url: str) -> bool:
    parsed = urlparse(candidate_url)
    allowed_domain = normalize_domain(urlparse(substack_url).netloc)
    candidate_domain = normalize_domain(parsed.netloc)
    return candidate_domain == allowed_domain and "/p/" in parsed.path

