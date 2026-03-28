"""
Scrape a full Substack article and summarize it using the Claude API.
Returns a structured summary dict ready for Notion page creation.
"""

import json
import os
import re
import subprocess
import tempfile
import time

import anthropic

SUMMARY_PROMPT = """\
You are a research assistant. Read the following article and produce a concise, \
accurate summary.

Article Title: {title}

Article Content:
{content}

Respond in exactly this format, with no extra text before or after:

## Title
[5-8 word title that captures the core topic, no clickbait]

## TL;DR
[1-2 sentences capturing the core message]

## Key Takeaways
- [Takeaway 1]
- [Takeaway 2]
- [Takeaway 3]
- [Optional Takeaway 4]
- [Optional Takeaway 5]

## Why It Matters
[1 paragraph on broader significance or implications]

## Tags
[3-5 short topic tags, comma-separated, e.g. AI Strategy, Career, Productivity]
"""

MIN_CONTENT_LENGTH = 200
FIRECRAWL_ATTEMPTS = 3
ANTHROPIC_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 1.0
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def extract_publish_date(content: str) -> str:
    """
    Extract the publish date from scraped article content.
    Returns ISO date string (YYYY-MM-DD) or empty string if not found.
    """
    # Match "Feb 26, 2026" or "Mar 4, 2026"
    match = re.search(
        r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(20\d{2})\b',
        content, re.IGNORECASE
    )
    if match:
        month = MONTH_MAP[match.group(1).lower()]
        day = match.group(2).zfill(2)
        year = match.group(3)
        return f"{year}-{month}-{day}"
    return ""


def extract_article_title(content: str) -> str:
    """
    Extract the real article title from scraped markdown content.
    Looks for the first H1 or H2 heading that isn't a site/nav element.
    Returns empty string if not found.
    """
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("## ") or line.startswith("# "):
            title = line.lstrip("#").strip()
            # Skip headings with images/links or that are too short
            if len(title) > 20 and "![" not in title and "](" not in title:
                return title
    return ""

