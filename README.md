# 🚀 Git Standup Bot

**AI-powered CLI tool that generates daily standup reports from your git activity.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

Git Standup Bot scans your git repositories, parses recent commits, groups them by type (using [Conventional Commits](https://www.conventionalcommits.org/)), and renders a beautiful standup report — right in your terminal. Optionally, it uses AI (OpenAI or local Ollama) to generate a natural-language summary.

## ✨ Features

- 📊 **Beautiful Terminal Output** — Rich tables, panels, and emoji via `rich`
- 🏷️ **Conventional Commit Grouping** — Auto-detects `feat`, `fix`, `docs`, `refactor`, etc.
- 🤖 **AI Summary (Optional)** — OpenAI GPT-4o-mini or local Ollama
- 📁 **Multi-Repo Support** — Scan multiple repositories in one go
- 📝 **Markdown Export** — Save reports as `.md` files
- ⚙️ **Configurable** — `.standup.toml` config file with sensible defaults
- 🎯 **Zero Config Required** — Works out of the box on any git repo

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/git-standup-bot.git
cd git-standup-bot

# Install with pip
pip install -e .

# Or with uv (recommended)
uv pip install -e .
```

## 🚀 Quick Start

```bash
# Run in any git repository — shows commits from yesterday
standup

# Custom time range
standup --since "3 days ago"
standup --since "2026-07-01"

# Multiple repositories
standup -r ~/projects/api -r ~/projects/frontend

# With AI-powered summary (requires OPENAI_API_KEY)
export OPENAI_API_KEY="sk-..."
standup --ai

# Using local Ollama instead
standup --ai --provider ollama

# Export to Markdown
standup --export standup-report.md

# Show commit hashes
standup --hashes

# Group by branch instead of type
standup --group-by branch

# Combine everything
standup -r ~/projects/* --ai --since "yesterday" --export report.md --hashes
```

## 🖥️ Example Output

```
╭─────────────────────────────────────────────────╮
│  🚀 Standup Report — 2026-07-06 (Sunday)        │
│  Author: John Doe │ Repos: 2 │ Commits: 8       │
╰─────────────────────────────────────────────────╯

  📦 api-backend  (5 commits)
┌────────────────┬──────────────────────────────────┐
│ Category       │ Changes                          │
├────────────────┼──────────────────────────────────┤
│ ✨ Features    │ Add user authentication endpoint │
│                │ Implement rate limiting           │
│ 🐛 Bug Fixes  │ Fix token refresh logic           │
│ 📝 Docs       │ Update API documentation          │
│ ♻️ Refactoring │ Clean up middleware chain         │
└────────────────┴──────────────────────────────────┘

  📦 frontend-app  (3 commits)
┌────────────────┬──────────────────────────────────┐
│ Category       │ Changes                          │
├────────────────┼──────────────────────────────────┤
│ ✨ Features    │ Add dark mode toggle             │
│ 🎨 Style      │ Refactor component styles         │
│ 🧪 Tests      │ Add unit tests for auth flow      │
└────────────────┴──────────────────────────────────┘

╭─────────────────────────────────────────────────╮
│  🤖 AI Summary:                                  │
│  Yesterday I focused on two main areas:          │
│  • Backend: Added auth endpoint with rate        │
│    limiting and fixed token refresh bugs         │
│  • Frontend: Implemented dark mode and           │
│    cleaned up component styles                   │
╰─────────────────────────────────────────────────╯
```

## ⚙️ Configuration

Create a `.standup.toml` file in your home directory or project root:

```toml
[general]
author = "John Doe"         # Default author filter
since = "yesterday"         # Default time range
timezone = "Europe/Istanbul" # Timezone for report headers

[repos]
paths = [
    "~/projects/api",
    "~/projects/frontend",
]

[ai]
enabled = false             # Set to true to always use AI
provider = "openai"         # "openai" or "ollama"
openai_model = "gpt-4o-mini"
ollama_model = "llama3.1"
ollama_url = "http://localhost:11434"

[output]
export_path = ""            # Auto-export path (empty = disabled)
show_hashes = false         # Show commit hashes
group_by = "type"           # "type", "branch", or "repo"
```

See [.standup.example.toml](.standup.example.toml) for a full example.

## 🧪 Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=standup --cov-report=term-missing
```

## 📋 CLI Reference

```
Usage: standup [OPTIONS]

Options:
  -s, --since TEXT        Time range for commits (default: yesterday)
  -a, --author TEXT       Filter by author name
  -r, --repos DIRECTORY   Repository paths (can specify multiple)
  --ai / --no-ai          Enable/disable AI summary
  -p, --provider TEXT     AI provider: openai or ollama
  -e, --export PATH       Export report to Markdown file
  -g, --group-by TEXT     Group by: type, branch, or repo
  --hashes / --no-hashes  Show/hide commit hashes
  -c, --config PATH       Path to .standup.toml config file
  --version               Show version
  -h, --help              Show this message and exit
```

## 🏗️ Architecture

```
src/standup/
├── cli.py              # Click CLI entry point
├── git_parser.py       # Git log parsing via subprocess
├── grouper.py          # Commit grouping (type/branch/repo)
├── ai_summarizer.py    # OpenAI + Ollama integration
├── formatter.py        # Rich terminal + Markdown output
└── config.py           # TOML config loader
```

## 📄 License

MIT — see [LICENSE](LICENSE)
