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


def scrape_substack_index(url: str) -> dict:
    """
    Run firecrawl scrape on the Substack index page.
    Returns the parsed JSON output from Firecrawl.
    Raises RuntimeError if firecrawl exits non-zero.
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
                        "--format",
                        "markdown,links",
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
                        f"Firecrawl timed out scraping the Substack index after {FIRECRAWL_ATTEMPTS} attempts."
                    ) from exc
                time.sleep(delay)
                delay *= 2
                continue

            if result.returncode == 0:
                try:
                    with open(output_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except json.JSONDecodeError as exc:
                    if attempt == FIRECRAWL_ATTEMPTS:
                        raise RuntimeError(
                            "Firecrawl returned invalid JSON for the Substack index scrape."
                        ) from exc
            else:
                error_message = (
                    f"Firecrawl failed (exit {result.returncode}): {result.stderr.strip()}"
                )
                if (
                    attempt == FIRECRAWL_ATTEMPTS
                    or not is_retryable_firecrawl_error(error_message)
                ):
                    raise RuntimeError(error_message)

            time.sleep(delay)
            delay *= 2

        raise RuntimeError("Firecrawl index scrape exhausted retries.")

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def parse_articles_from_scrape(scrape_data: dict, substack_url: str) -> list:
    """
    Extract article entries from the Firecrawl output.
    Filters to only /p/ subpaths (actual posts, not archive/about pages).
    Returns list of {"url": str, "title": str, "slug": str}.
    """
    articles = []
    seen_urls = set()

    # Try structured links first
    links = scrape_data.get("links", [])
    for link in links:
        href = link.get("href", "") if isinstance(link, dict) else str(link)
        text = link.get("text", "") if isinstance(link, dict) else ""

        if not href:
            continue

        absolute_url = urljoin(substack_url, href)
        if not is_allowed_article_url(absolute_url, substack_url):
            continue

        parsed = urlparse(absolute_url)
        # Strip query strings and fragments for dedup
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        slug = parsed.path.split("/p/")[-1].rstrip("/")
        title = text.strip() if text.strip() else slug.replace("-", " ").title()

        articles.append({"url": clean_url, "title": title, "slug": slug})

    # Fallback: parse URLs from markdown content
    if not articles:
        markdown = scrape_data.get("markdown", "")
        pattern = r'https://[^/]+/p/([a-z0-9\-]+)'
        for match in re.finditer(pattern, markdown):
            full_url = match.group(0).rstrip(")")
            if not is_allowed_article_url(full_url, substack_url):
                continue

            parsed = urlparse(full_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            slug = parsed.path.split("/p/")[-1].rstrip("/")
            articles.append({
                "url": clean_url,
                "title": slug.replace("-", " ").title(),
                "slug": slug,
            })

    return articles


def get_article_list(substack_url: str) -> list:
    """
    Main entry point. Scrapes the Substack index and returns a list of article dicts.
    Raises ValueError if no articles are found (possible page structure change).
    """
    scrape_data = scrape_substack_index(substack_url)
    articles = parse_articles_from_scrape(scrape_data, substack_url)

    if not articles:
        raise ValueError(
            "No articles found in Substack scrape. "
            "The page structure may have changed or the scrape failed."
        )

    return articles
