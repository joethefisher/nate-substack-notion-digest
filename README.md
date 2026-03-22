# Nate's Newsletter Digest

I’ve always valued Nate’s work, but I rarely had time to keep up with both his YouTube content and his Substack articles. I’d get the emails, save them with good intentions, and then never actually make time to read the full posts. That’s why I built this summarizer: to help me stay current on his content in a way that fits my workflow.

Automates a daily Substack-to-Notion reading workflow:

- scrapes new posts from `natesnewsletter.substack.com`
- summarizes each article with Anthropic
- creates structured Notion pages for later reading
- stores local state so previously processed posts are skipped

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

Notes:

- `--dry-run` performs scraping and summarization but skips Notion writes and processed-state updates.
- Runtime paths are resolved relative to the repository root, so the script can be launched from any working directory.
- A run lock prevents overlapping executions from publishing duplicate pages.

## Example Output

```text
2026-03-21 20:56:41 [INFO] Found 8 total articles
2026-03-21 20:56:53 [INFO] [DRY RUN] Would create Notion page: AI Agents Excel at Tasks, Fail at Jobs
2026-03-21 20:58:12 [INFO] Done. Processed: 8, Failed/Skipped: 0
```

## Tests

```bash
./.venv/bin/python -m unittest discover -s tests -v
```

## Development

Install dev tooling:

```bash
./.venv/bin/pip install -r requirements-dev.txt
```

Lint:

```bash
./.venv/bin/ruff check .
```

Continuous integration runs tests and Ruff checks on every push via GitHub Actions.

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
