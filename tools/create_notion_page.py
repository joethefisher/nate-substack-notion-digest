"""
Create a Notion page in the digest database from a structured summary dict.
Uses the notion-client Python library.
"""

from datetime import datetime, timezone
import time

from notion_client import Client
from notion_client import errors

NOTION_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 1.0


def build_rich_text(text: str, chunk_size: int = 2000) -> list[dict]:
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [""]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def is_retryable_notion_error(exc: Exception) -> bool:
    if isinstance(exc, errors.RequestTimeoutError):
        return True

    status_code = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True

    error_code = str(getattr(exc, "code", "")).lower()
    return error_code in {"rate_limited", "service_unavailable", "internal_server_error"}


def get_notion_client(api_key: str) -> Client:
    return Client(auth=api_key)


def build_page_properties(summary: dict) -> dict:
    """
    Map summary fields to Notion page property schema.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    props = {
        "Name": {
            "title": [{"text": {"content": summary["title"][:2000]}}]
        },
        "URL": {
            "url": summary["url"]
        },
        "TL;DR": {
            "rich_text": build_rich_text(summary["tldr"][:2000])
        },
        "Status": {
            "select": {"name": "Unread"}
        },
        "Added": {
            "date": {"start": today}
        },
    }

    if summary.get("published_date"):
        props["Published"] = {"date": {"start": summary["published_date"]}}

    if summary.get("youtube_url"):
        props["Youtube URL"] = {"url": summary["youtube_url"]}

    if summary.get("tags"):
        props["Tags"] = {"multi_select": [{"name": t} for t in summary["tags"]]}

    return props


def build_page_content(summary: dict) -> list:
    """
    Build the Notion block children list for the page body.
    """
    blocks = []

    # TL;DR section
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "TL;DR"}}]
        },
    })
    blocks.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": build_rich_text(summary["tldr"])
        },
    })

    # Key Takeaways section
