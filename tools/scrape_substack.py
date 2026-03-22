"""
Scrape the Nate's Newsletter Substack index page and return a list of article dicts.
Uses the Firecrawl CLI (already installed and authenticated) via subprocess.
"""

import json
import os
import re
import subprocess
import tempfile
from urllib.parse import urlparse


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

        if result.returncode != 0:
            raise RuntimeError(
                f"Firecrawl failed (exit {result.returncode}): {result.stderr.strip()}"
            )

        with open(output_path, "r") as f:
            return json.load(f)

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def parse_articles_from_scrape(scrape_data: dict) -> list:
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

        parsed = urlparse(href)
        # Must be from the same domain and a post (/p/ path)
        if "/p/" not in parsed.path:
            continue
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
    articles = parse_articles_from_scrape(scrape_data)

    if not articles:
        raise ValueError(
            "No articles found in Substack scrape. "
            "The page structure may have changed or the scrape failed."
        )

    return articles
