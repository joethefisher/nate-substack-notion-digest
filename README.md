# Nate's Newsletter Digest

Automates a daily Substack-to-Notion reading workflow:

- scrapes new posts from `natesnewsletter.substack.com`
- summarizes each article with Anthropic
- creates structured Notion pages for later reading
- stores local state so previously processed posts are skipped

## Why This Exists

This project turns a newsletter feed into a personal research queue. It is designed to be reliable enough for unattended scheduled runs while still being simple to inspect and extend.

## Stack

- Python 3.10+
- Firecrawl CLI for scraping
- Anthropic Messages API for summarization
- Notion API for persistence

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Create a `.env` file with:

```env
ANTHROPIC_API_KEY=...
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
```

## Running

Dry run:

```bash
./.venv/bin/python run_digest.py --dry-run
```

Full run:

```bash
./.venv/bin/python run_digest.py --verbose
```

Notes:

- `--dry-run` performs scraping and summarization but skips Notion writes and processed-state updates.
- Runtime paths are resolved relative to the repository root, so the script can be launched from any working directory.
- A run lock prevents overlapping executions from publishing duplicate pages.

## Tests

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

## Project Structure

```text
run_digest.py                 Orchestrates the full workflow
tools/scrape_substack.py      Scrapes the Substack index and extracts article URLs
tools/check_new_articles.py   Loads and updates processed article state
tools/summarize_article.py    Scrapes article content and requests summaries
tools/create_notion_page.py   Builds and creates Notion pages
workflows/substack_digest.md  Human-readable operating notes for the workflow
```

## Operational Behavior

- Processed URLs are stored in `.tmp/processed_articles.json`
- Logs are written to `.tmp/digest.log`
- Paywalled or failed articles are skipped and retried on the next run
- State is only updated after a Notion page is successfully created
