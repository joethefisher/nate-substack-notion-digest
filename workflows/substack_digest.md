# Workflow: Nate's Newsletter Substack → Notion Digest

## Objective
Automatically scrape new articles from natesnewsletter.substack.com daily, summarize each using Claude, and create structured Notion pages for easy reading.

## Required Inputs
- `ANTHROPIC_API_KEY` — Claude API key (in `.env`)
- `NOTION_API_KEY` — Notion integration secret (required for non-dry runs)
- `NOTION_DATABASE_ID` — Target Notion database ID (required for non-dry runs)
- Firecrawl CLI authenticated (already done — run `firecrawl credit-usage` to verify)
