# 🚀 Git Standup Bot

**AI-powered CLI tool that generates daily standup reports from your git activity.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/Haarper23/git-standup-bot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Haarper23/git-standup-bot/actions/workflows/ci.yml)

---

Git Standup Bot scans your git repositories, parses recent commits, groups them by type (using [Conventional Commits](https://www.conventionalcommits.org/)), and renders a beautiful standup report — right in your terminal. Optionally, it uses AI (OpenAI, Google Gemini, or local Ollama) to generate a natural-language summary.

## ✨ Features

- 📊 **Beautiful Terminal Output** — Rich tables, panels, and emoji via `rich`
- 🏷️ **Conventional Commit Grouping** — Auto-detects `feat`, `fix`, `docs`, `refactor`, etc.
- 🤖 **AI Summary (Optional)** — OpenAI GPT-4o-mini, Google Gemini, or local Ollama
- 🕵️ **Tech Lead AI Agent (Optional)** — Analyze risk, architecture, and code quality in commits
- 📁 **Multi-Repo Support** — Scan multiple repositories in one go
- 📝 **Markdown Export** — Save reports as `.md` files
- ⚙️ **Configurable** — `.standup.toml` config file with sensible defaults
- 🎯 **Zero Config Required** — Works out of the box on any git repo
- 🔒 **Encoding-Safe Output** — Automated CP1254/ASCII fallbacks for Windows CMD/PowerShell compatibility

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Haarper23/git-standup-bot.git
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

## 🕵️ AI Standup Agent vs AI Summarizer vs Tech Lead Agent

Git Standup Bot includes three distinct AI capabilities:

1. **AI Summarizer** (enabled via `--ai`): Generates a free-form, conversational daily standup summary of recent work.
2. **Tech Lead Agent** (enabled via `--agent`): Performs high-level architectural, risk, and security analysis of code changes.
3. **AI Standup Agent** (enabled via `--standup-agent`): Organizes parsed Git activity into exactly four structured sections:
   - **Completed**: Features, fixes, documentation, refactorings, etc.
   - **In Progress**: Active draft/WIP items.
   - **Risks / Blockers**: Reverts, regressions, or explicit blocking items.
   - **Next Steps**: Actionable, conservative items derived from WIP and risk signals.

### CLI Usage Example

```bash
# Enable the AI Standup Agent using the auto-detected AI provider
standup --standup-agent

# Enable offline, deterministic fallback mapping (runs without AI credentials or API calls)
standup --standup-agent --no-ai
```

### Fallback & Security Boundaries
* **Opt-In Behavior**: The AI Standup Agent is fully opt-in and disabled by default. It is separate from the `--agent` switch, which controls the Tech Lead Agent.
* **Supported Provider Values**: The supported AI provider values are exactly `auto`, `openai`, `gemini`, and `ollama`.
* **Invalid Provider Configuration**: Providing an invalid provider value from CLI, TOML config, or environment variables fails clearly with a non-zero exit code and controlled error message instead of silently falling back.
* **Connection Failures**: Expected connection and network-related errors (such as `URLError`, `HTTPError`, `TimeoutError`, `ConnectionError`, `OSError`) trigger deterministic offline fallback gracefully.
* **Explicit Provider Isolation**: Explicitly choosing a provider (e.g. `--provider gemini` or `--provider ollama`) routes requests strictly to that provider. Explicit providers do not probe alternatives or search local backends.
* **Ollama Discovery Envelope Validation**: Ollama local model discovery performs strict direct validation of the models/tags list returned by the local backend, preventing raw data indexing errors.
* **Wrapper Validation**: Provider wrapper responses (including Gemini candidates and Ollama response blocks) are strictly validated before use, and malformed envelopes trigger deterministic fallback.
* **UTF-8 Byte Bounding**: Commit context and complete prompts are strictly bounded by UTF-8 byte size rather than simple character counts.
* **Error Propagation**: Unexpected internal programming errors (e.g. `TypeError`, `AttributeError`, `AssertionError`) are not hidden as offline fallback, allowing them to propagate normally.
* **Security & Sandboxing**: The agent runs purely read-only, never performs Git writes, never creates commits, never pushes, and never runs arbitrary shell commands.




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
provider = "auto"           # "auto", "openai", "ollama", or "gemini"
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
  -s, --since TEXT                Time range for commits (default: yesterday)
  -a, --author TEXT               Filter by author name
  -r, --repos DIRECTORY           Repository paths (can specify multiple)
  --ai / --no-ai                  Enable/disable AI summary
  --agent / --no-agent            Enable Tech Lead AI Agent
  --standup-agent / --no-standup-agent
                                  Enable/disable AI Standup Agent
  -p, --provider TEXT             AI provider: auto, openai, ollama, or gemini
  -e, --export PATH               Export report to Markdown file
  -g, --group-by TEXT             Group by: type, branch, or repo
  --hashes / --no-hashes          Show/hide commit hashes
  -c, --config PATH               Path to .standup.toml config file
  --version                       Show version
  -h, --help                      Show this message and exit

```

## 🌿 Branch Grouping Limitations

When using `--group-by branch`, Git Standup Bot groups commits by their active branch tip decorations (retrieved using `%D` format in `git log`).

> [!NOTE]
> **Git limitation:** Git is content-addressable and commit-history is a directed acyclic graph. Commits do not store the name of the branch they were originally committed to.
> Therefore, once branches are merged, or if commits are historical parents, direct branch ref decorations are not present. Undecorated historical commits will default to the currently checked-out branch at runtime.

## 🏗️ Architecture

```
src/standup/
├── cli.py              # Click CLI entry point
├── encoding_helper.py  # CP1254/ASCII stream-writing sanitization
├── timezone_helper.py  # Shared timezone resolution boundary
├── git_parser.py       # Git log parsing via subprocess
├── grouper.py          # Commit grouping (type/branch/repo)
├── ai_summarizer.py    # OpenAI + Ollama + Gemini integration
├── formatter.py        # Rich terminal + Markdown output
└── config.py           # TOML config loader
```

## 📄 License

MIT — see [LICENSE](LICENSE)
