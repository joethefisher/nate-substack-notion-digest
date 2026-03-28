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


def extract_youtube_url(content: str) -> str:
    """
    Extract the first YouTube URL from scraped article content.
    Returns URL string or empty string if not found.
    """
    match = re.search(
        r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w\-]+',
        content
    )
    return match.group(0) if match else ""


def is_retryable_firecrawl_error(message: str) -> bool:
    lowered = message.lower()
    retry_markers = [
        "timeout",
        "timed out",
        "rate limit",
        "429",
        "500",
        "502",
        "503",
        "504",
        "temporary",
    ]
    return any(marker in lowered for marker in retry_markers)


def should_retry_anthropic_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.InternalServerError,
            anthropic.RateLimitError,
        ),
    ):
        return True

    status_code = getattr(exc, "status_code", None)
    return status_code in {408, 409, 429, 500, 502, 503, 504}


def scrape_article_content(url: str) -> str:
    """
    Use Firecrawl CLI to scrape full article text.
    Returns the markdown content string.
    Raises RuntimeError if scrape fails.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as tmp:
        output_path = tmp.name

    try:
        delay = INITIAL_RETRY_DELAY_SECONDS
        for attempt in range(1, FIRECRAWL_ATTEMPTS + 1):
            try:
                result = subprocess.run(
                    [
                        "firecrawl",
                        "scrape",
                        url,
                        "--only-main-content",
                        "-o",
                        output_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired as exc:
                if attempt == FIRECRAWL_ATTEMPTS:
                    raise RuntimeError(
                        f"Firecrawl timed out scraping article after {FIRECRAWL_ATTEMPTS} attempts: {url}"
                    ) from exc
                time.sleep(delay)
                delay *= 2
                continue

            if result.returncode == 0:
                try:
                    with open(output_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    return data.get("markdown", "")
                except json.JSONDecodeError as exc:
                    if attempt == FIRECRAWL_ATTEMPTS:
                        raise RuntimeError(
                            f"Firecrawl returned invalid JSON for article scrape: {url}"
                        ) from exc
            else:
                error_message = (
                    f"Firecrawl failed scraping article (exit {result.returncode}): "
                    f"{result.stderr.strip()}"
                )
                if (
                    attempt == FIRECRAWL_ATTEMPTS
                    or not is_retryable_firecrawl_error(error_message)
                ):
                    raise RuntimeError(error_message)

            time.sleep(delay)
            delay *= 2

        raise RuntimeError(f"Firecrawl scrape exhausted retries for article: {url}")

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def parse_summary_response(raw: str) -> dict:
    """
    Parse Claude's structured response into a dict with keys:
    tldr, key_takeaways (list), why_it_matters.
    Falls back gracefully if sections are missing.
    """
    tldr = ""
    takeaways = []
    why = ""
    title = ""

    title_match = re.search(
        r"## Title\s*\n(.*?)(?=\n## |\Z)", raw, re.DOTALL
    )
    if title_match:
        title = title_match.group(1).strip()

    tldr_match = re.search(
        r"## TL;DR\s*\n(.*?)(?=\n## |\Z)", raw, re.DOTALL
    )
    if tldr_match:
        tldr = tldr_match.group(1).strip()

    takeaways_match = re.search(
        r"## Key Takeaways\s*\n(.*?)(?=\n## |\Z)", raw, re.DOTALL
    )
    if takeaways_match:
        lines = takeaways_match.group(1).strip().splitlines()
        takeaways = [
            line.lstrip("- •").strip()
            for line in lines
            if line.strip().startswith(("-", "•"))
        ]

    why_match = re.search(
        r"## Why It Matters\s*\n(.*?)(?=\n## |\Z)", raw, re.DOTALL
    )
    if why_match:
        why = why_match.group(1).strip()

    tags = []
    tags_match = re.search(
        r"## Tags\s*\n(.*?)(?=\n## |\Z)", raw, re.DOTALL
    )
    if tags_match:
        tags = [t.strip() for t in tags_match.group(1).strip().split(",") if t.strip()]

    return {
        "generated_title": title,
        "tldr": tldr or raw[:300],
        "key_takeaways": takeaways or ["See full summary below."],
        "why_it_matters": why or "",
        "tags": tags,
    }


def summarize_article(url: str, title: str, api_key: str) -> dict:
    """
    Full pipeline: scrape article -> call Claude API -> parse response.
    Returns a summary dict:
    {
        "url": str,
        "title": str,
        "tldr": str,
        "key_takeaways": list[str],
        "why_it_matters": str,
    }
    Raises ValueError if article content is too short (likely paywalled).
    Raises RuntimeError on scrape failure.
    """
    content = scrape_article_content(url)
    article_title = extract_article_title(content) or title

    if len(content.strip()) < MIN_CONTENT_LENGTH:
        raise ValueError(
            f"Article content too short ({len(content)} chars) — "
            f"possibly paywalled or failed to scrape: {url}"
        )

    prompt = SUMMARY_PROMPT.format(
        title=article_title,
        content=content[:12000],  # cap to avoid token limits
    )

    client = anthropic.Anthropic(api_key=api_key)
    delay = INITIAL_RETRY_DELAY_SECONDS
    last_exception = None
    for attempt in range(1, ANTHROPIC_ATTEMPTS + 1):
        try:
            message = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_response = "".join(
                block.text
                for block in message.content
                if getattr(block, "type", "") == "text"
            ).strip()
            if not raw_response:
                raise RuntimeError("Anthropic returned an empty summary response.")
            break
        except Exception as exc:
            last_exception = exc
            if attempt == ANTHROPIC_ATTEMPTS or not should_retry_anthropic_error(exc):
                raise
            time.sleep(delay)
            delay *= 2
    else:
        raise RuntimeError("Anthropic summary request exhausted retries.") from last_exception

    parsed = parse_summary_response(raw_response)

    return {
        "url": url,
        "title": parsed.get("generated_title") or article_title,
        "published_date": extract_publish_date(content),
        "youtube_url": extract_youtube_url(content),
        **parsed,
    }
