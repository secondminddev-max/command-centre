# ChromaDB Semantic Memory Integration
**Date:** 2026-03-15
**Type:** New capability — open-source tool integration

## What was built
Integrated **ChromaDB** (v1.5.5, 26k stars, actively maintained) as a persistent
semantic vector database powering a new MemoryAgent.

## Components

### 1. MemoryAgent (`memoryagent`)
- Spawned as a live background agent in the agent system
- Indexes content from 4 data sources every 10 minutes:
  - `data/hn_top.json` — HackerNews top stories
  - `data/tech_news_latest.json` — latest tech news
  - `data/github_trending.json` — GitHub trending repos
  - `data/wiki_facts.json` — Wikipedia facts
- Stores 35+ documents with sentence-transformer embeddings in
  `data/chromadb/` (persistent, survives restarts)

### 2. Semantic Search HTTP server (port 5051)
- Lightweight HTTP server embedded in the MemoryAgent
- API: `GET http://localhost:5051/?q=your+query&n=5`
- Returns ranked results with cosine similarity scores
- Handles deduplication via upsert (safe to re-index)

### 3. Dashboard widget (`agent-command-centre.html`)
- New "🧠 Semantic Search" panel in bottom-right of grid (col 3, row 2)
- Input box + search button, Enter key supported
- Shows live indexed item count polled every 10s
- Displays results with score, source tag, and clickable URL

## Tool files
- `tools/spawn_memoryagent.py` — initial spawn script
- `tools/upgrade_memoryagent.py` — upgraded version with reliable indexing

## Why ChromaDB
- Fills a genuine capability gap: agents collect raw data but had no way to
  ask "what have I seen that's similar to X?"
- Fully local (SQLite-backed), no API keys, no cloud dependency
- pip-installable in one command
- Enables future capabilities: semantic deduplication, cross-agent memory
  sharing, intelligent briefing generation
