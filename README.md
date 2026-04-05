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

## Requirements

- Python 3.10 or newer
- Firecrawl CLI installed and authenticated
- Anthropic API key
- Notion API key and target database ID for non-dry runs

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
