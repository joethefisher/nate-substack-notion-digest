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


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE),
        ],
    )


def ensure_runtime_dirs() -> None:
    TMP_DIR.mkdir(exist_ok=True)


@contextmanager
def acquire_run_lock():
    with open(LOCK_FILE, "w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another digest run is already in progress.") from exc
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def validate_env(require_notion: bool) -> tuple[str, str | None, str | None]:
    """
    Check required env vars are present. Returns (anthropic_key, notion_key, db_id).
    Raises EnvironmentError listing missing vars.
    """
    required = {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }
    if require_notion:
        required["NOTION_API_KEY"] = os.getenv("NOTION_API_KEY")
        required["NOTION_DATABASE_ID"] = os.getenv("NOTION_DATABASE_ID")

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please add them to your .env file."
        )
    return (
        required["ANTHROPIC_API_KEY"],
        required.get("NOTION_API_KEY"),
        required.get("NOTION_DATABASE_ID"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Nate's Newsletter digest automation")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and summarize but skip Notion page creation and state updates",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    ensure_runtime_dirs()
    setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    if args.dry_run:
        log.info("--- DRY RUN MODE: Notion pages will NOT be created ---")

    # Validate environment
    try:
        anthropic_key, notion_key, notion_db_id = validate_env(
            require_notion=not args.dry_run
        )
    except EnvironmentError as e:
        log.error(str(e))
        return 2

    # Import tools here so env is loaded first
    from tools.scrape_substack import get_article_list
    from tools.check_new_articles import (
        load_processed_state,
        filter_new_articles,
        mark_article_processed,
        save_processed_state,
    )
    from tools.summarize_article import summarize_article
    from tools.create_notion_page import create_notion_page

    try:
        with acquire_run_lock():
            # Step 1: Scrape article list
            log.info(f"Scraping article list from {SUBSTACK_URL}")
            try:
                all_articles = get_article_list(SUBSTACK_URL)
                log.info(f"Found {len(all_articles)} total articles")
            except (RuntimeError, ValueError) as e:
                log.error(f"Failed to scrape Substack index: {e}")
                return 2

            # Step 2: Filter to new articles
            state = load_processed_state()
            new_articles = filter_new_articles(all_articles, state)
            log.info(f"{len(new_articles)} new article(s) to process")

            if not new_articles:
                log.info("No new articles. Nothing to do.")
                return 0

            # Step 3: Process each new article
            failures = []
            processed_count = 0

            for article in new_articles:
                url = article["url"]
                title = article["title"]
                log.info(f"Processing: {title}")
                log.debug(f"  URL: {url}")

                # Summarize
                try:
                    summary = summarize_article(url, title, anthropic_key)
                    log.info("  Summarized OK")
                    log.debug(f"  TL;DR: {summary['tldr'][:120]}...")
                except ValueError as e:
                    log.warning(f"  Skipping (likely paywalled): {e}")
                    failures.append({"url": url, "reason": str(e)})
                    continue
                except Exception as e:
                    log.error(f"  Summarization failed: {e}")
                    failures.append({"url": url, "reason": str(e)})
                    continue

                # Create Notion page
                if args.dry_run:
                    log.info(f"  [DRY RUN] Would create Notion page: {summary['title']}")
                else:
                    try:
                        page_url = create_notion_page(summary, notion_db_id, notion_key)
                        log.info(f"  Notion page created: {page_url}")
                    except Exception as e:
                        log.error(f"  Notion page creation failed: {e}")
                        failures.append({"url": url, "reason": str(e)})
                        # Do NOT mark as processed — will retry next run
                        continue

                    # Save state after each successful page creation
                    state = mark_article_processed(url, state)
                    save_processed_state(state)

                processed_count += 1

            # Summary
            log.info(
                f"Done. Processed: {processed_count}, Failed/Skipped: {len(failures)}"
            )
            if failures:
                for f in failures:
                    log.warning(f"  SKIPPED: {f['url']} — {f['reason']}")

            return 0 if not failures else 1
    except RuntimeError as e:
        log.error(str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
