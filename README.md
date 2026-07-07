# 🚀 Git Standup Bot

**AI-powered CLI tool that generates daily standup reports from your git activity.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CI](https://github.com/Haarper23/git-standup-bot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Haarper23/git-standup-bot/actions/workflows/ci.yml)

---

## 📖 Project Overview

Git Standup Bot is a productivity tool designed to streamline daily standup preparation. It works by:
- **Reading Git commit activity** across one or more repositories for a specified time window.
- **Grouping work by repository and category** using conventional commit types (e.g., features, bug fixes, documentation).
- **Generating daily standup reports** rendered directly in your terminal.
- **Supporting deterministic offline reporting** with zero external dependencies, API keys, or LLM calls.
- **Optionally using AI providers** to summarize and analyze your work.
- **Including a separate, read-only AI Standup Agent** to automatically categorize achievements, in-progress items, and blockers.
- **Running strictly read-only**—it does not modify Git repositories, write git state, create tags, or alter branches in any way.

---

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

---

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

---

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

---

## 🖥️ Example Output

```
+-----------------------------------------------------------------------------+
|                                                                             |
|  [Standup] Standup Report — 2026-07-06 (Monday)                             |
|  Author: John Doe | Repos: 2 | Commits: 8                                   |
|                                                                             |
+-----------------------------------------------------------------------------+

  [Repo] api-backend  (5 commits)
+-----------------------------------------------------------------------------+
| Category         | Changes                                                  |
|------------------+----------------------------------------------------------|
| [Feature] Features      | Add user authentication endpoint                         |
|                  | Implement rate limiting                                  |
| [Fix] Bug Fixes     | Fix token refresh logic                                  |
| [Docs] Docs         | Update API documentation                                 |
| [Refactor] Refactor | Clean up middleware chain                                |
+-----------------------------------------------------------------------------+

  [Repo] frontend-app  (3 commits)
+-----------------------------------------------------------------------------+
| Category         | Changes                                                  |
|------------------+----------------------------------------------------------|
| [Feature] Features      | Add dark mode toggle                                     |
| [Style] Style       | Refactor component styles                                |
| [Test] Tests        | Add unit tests for auth flow                             |
+-----------------------------------------------------------------------------+

+-----------------------------------------------------------------------------+
|                                                                             |
|  [AI] AI Summary:                                                           |
|  Yesterday I focused on two main areas:                                     |
|  • Backend: Added auth endpoint with rate limiting and fixed token refresh  |
|    bugs                                                                     |
|  • Frontend: Implemented dark mode and cleaned up component styles          |
|                                                                             |
+-----------------------------------------------------------------------------+
```

---

## 📊 Output Modes

Git Standup Bot supports four distinct output and analysis modes:

1. **Deterministic Report (Default)**: Parses your local git commits, organizes them by category (e.g., Features, Bug Fixes), and displays a tabular report. This mode runs locally, performs no AI/LLM queries, and does not require internet access or API credentials.
2. **AI Summary** (enabled via `--ai`): Leverages an LLM provider to synthesize recent commit history into a natural-language, conversational summary of your contributions.
3. **Tech Lead Agent** (enabled via `--agent`): Performs architectural, risk, and security assessments of code changes to highlight potential design concerns.
4. **AI Standup Agent** (enabled via `--standup-agent`): Organizes commit activity into exactly four structured sections:
   - **Completed**: Features, fixes, documentation, refactorings, etc.
   - **In Progress**: Active draft/WIP items.
   - **Risks / Blockers**: Reverts, regressions, or explicit blocking items.
   - **Next Steps**: Actionable, conservative items derived from WIP and risk signals.

> [!IMPORTANT]
> **AI Flag Semantics (`--no-ai`)**:
> - `--no-ai` disables provider-backed AI Summary generation and forces the AI Standup Agent to use its deterministic local fallback.
> - **Note**: `--no-ai` does **not** automatically disable the separate Tech Lead Agent. If `--agent` remains enabled, the Tech Lead Agent may still invoke its configured provider path.
> - To run in a completely provider-free/offline mode with zero LLM/external backend requests, you must ensure the Tech Lead Agent is disabled as well (e.g., by ensuring `--agent` is not enabled, or passing `--no-agent`).
> - The deterministic fallback is not an LLM and runs purely using rules-based regex classifiers.

---

## 🤖 Supported AI Providers

The following providers are supported:
- **`auto`**: Automatically resolves the best available provider based on environment signals.
- **`openai`**: Routes to OpenAI (requires `OPENAI_API_KEY`).
- **`gemini`**: Routes to Google Gemini (requires `GEMINI_API_KEY`).
- **`ollama`**: Routes to a local Ollama server running on `http://localhost:11434` (requires no API keys).

### Provider Routing & Isolation Rules:
- **Strict Explicit-Provider Isolation (AI Standup Agent Only)**: For the new AI Standup Agent, choosing a specific provider (e.g., `--provider gemini` or `--provider ollama`) routes requests strictly to that provider:
  - `provider=openai` only attempts OpenAI.
  - `provider=gemini` only attempts Gemini.
  - `provider=ollama` only attempts Ollama.
  - Specifying an invalid provider name will immediately fail with a non-zero exit code and a clear error message before any provider calls are initiated.
  - `provider=auto` resolves using: `Ollama -> Gemini -> OpenAI`.
- **Existing AI Summary & Tech Lead Agent Provider Behavior**: The existing AI Summary and Tech Lead Agent use their existing automatic routing behavior. Specifically, they may inspect local Ollama availability before selecting a remote provider, and they do not provide the same strict explicit-provider isolation guarantee as the new AI Standup Agent.
- **Provider Fallbacks**: Expected connection and network failures (such as timeouts, offline status, or endpoint errors) trigger a graceful fallback to local deterministic output mode.
- **No-AI Flag**: Using `--no-ai` disables provider-backed AI Summary generation and forces the AI Standup Agent to use its deterministic fallback. To guarantee a fully offline run with no provider requests whatsoever, ensure `--agent` is disabled (or pass `--no-agent`).

---

## 🔌 Automatic Provider Selection

When `--provider auto` (default) is used with `--ai` or `--standup-agent`, Git Standup Bot resolves the backend in the following priority order:
1. **Ollama**: Automatically checked first. If a local Ollama server is running at the configured URL and contains at least one installed model, the bot selects Ollama.
2. **Gemini**: Selected if `GEMINI_API_KEY` is present in the environment variables.
3. **OpenAI**: Selected if `OPENAI_API_KEY` is present in the environment variables.

If no active provider backend is found, the system defaults to deterministic offline output without performing any network requests.

---

## 🦙 Local Ollama Setup (Windows Quick Start)

You can run Git Standup Bot completely offline using a local LLM.

### 1. Verify Ollama Installation
Ensure Ollama is installed and running on your system by executing the following commands in PowerShell:
```powershell
# Set workspace location (portable example)
Set-Location path\to\git-standup-bot

# Check Ollama CLI version
ollama --version

# List downloaded models
ollama ls

# Query local server API version
Invoke-RestMethod http://localhost:11434/api/version
```

### 2. Download a Model
A compatible model must be pulled before running. You can pull any compatible model (e.g., `llama3.1:8b`):
```powershell
ollama pull llama3.1:8b
```
*(Note: `llama3.1:8b` is not mandatory; any compatible model returned by Ollama's local discovery list will be automatically detected and selected.)*

### 3. Run Git Standup Bot with Ollama
To generate a standup report with the AI Standup Agent using Ollama:
```powershell
.\.venv\Scripts\python.exe -m standup.cli --standup-agent --ai --provider ollama --no-agent --since "30 days ago"
```

### 4. Manage running models
To check which model is active in GPU/RAM:
```powershell
ollama ps
```
To unload a model from memory and release system GPU/RAM resources:
```powershell
ollama stop llama3.1:8b
```
*(Note: The model name provided to `ollama stop` must exactly match the model loaded in memory.)*

---

## 🔌 Offline Modes

You can run the Git Standup Bot completely offline without any AI APIs or models:

### 1. Deterministic Text Report
```powershell
.\.venv\Scripts\python.exe -m standup.cli --since "30 days ago" --no-ai --no-agent --no-standup-agent
```
This command disables all optional AI modes (AI Summary, Tech Lead Agent, and AI Standup Agent), rendering only the local conventional commit summary tables.

### 2. Deterministic Standup Agent Fallback
```powershell
.\.venv\Scripts\python.exe -m standup.cli --standup-agent --no-ai --no-agent --since "30 days ago"
```
This command enables the Standup Agent interface, but forces it to use local rules-based regex classifiers instead of contacting an LLM provider.

**Details**:
- Neither command contacts any AI provider or makes network requests.
- No model calls or external API queries are initiated.
- No API keys or credentials are required.
- The deterministic fallback is not an LLM.

---

## 🔒 Security Model & Sandboxing

The AI Standup Agent is designed to be **read-only and tightly sandboxed**:
- **No Command Execution**: The agent never executes shell commands or runs model-generated code.
- **Read-Only Git Operations**: It never writes Git state, commits, pushes, switches branches, or alters repository metadata.
- **Local Isolation**: It does not open model-provided file paths or access external URLs.
- **Strict Privacy**: It never transmits full repository source files, diffs, environment variables, or private API keys to the model backend.
- **Bounded Context**: Context size is strictly capped. Commit summaries and prompts are limited to a maximum number of bytes, ensuring no accidental leakage or buffer overflows.

---

## 💻 Windows Verification & Tested Environment

The following environment has been verified:
- **OS**: Windows (PowerShell Core / Command Prompt)
- **Ollama Backend**: Version 0.31.1 running locally at `http://localhost:11434`
- **Model**: `llama3.1:8b` (executing with GPU acceleration)
- **Output Safety**: Validated against Windows terminal encoding limits (CP1254 and CP850 fallback handlers)
- **Tests**: Verified four-section AI Standup Agent generation and conversational AI summaries.

*(Note: The above setup represents a tested configuration, not a minimum requirement. Other OS versions, Ollama versions, CPU-only systems, or models may be used.)*

---

## ⚠️ Limitations

- **Commit Message Quality**: Output and classification quality directly depend on the descriptiveness of your commit messages.
- **Small Model Accuracy**: Smaller local models (e.g., <= 8B parameters) may occasionally misclassify complex tasks or generate imperfect grammar.
- **Branch Grouping Limitations**: Branch categorization depends on available active Git decorations (ref tips) in your local repository; historical parent branches are not preserved.
- **Metadata Only**: The bot analyzes commit subjects and metadata only. It does not ingest entire codebases or possess deep semantic code understanding.
- **API Availability**: If external APIs (OpenAI/Gemini) are rate-limited or offline, the tool falls back to deterministic rules.

---

## 🧪 Testing and CI

Git Standup Bot has a comprehensive test suite validated against multiple platforms and Python versions:
- **Total Tests**: 127 tests
- **Targeted Agent Tests**: 64 tests verifying boundaries, provider errors, and fallback logic
- **Supported Matrix**: Python 3.10, 3.11, 3.12, and 3.13
- **CI Platforms**: Ubuntu (Linux) and Windows
- **CI Coverage**: The latest verified main-branch run passed all eight matrix jobs.

```bash
# Run full test suite locally
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## 🚀 Release Status

**Current Target**: `v1.0.0` (Pending Release)

This release represents the first public MVP focusing on developer productivity, featuring:
- Deterministic local Git reporting.
- Smart AI provider routing and local Ollama model auto-discovery.
- Bounded prompts and envelope-validation security hardening.
- Tech Lead AI Agent and the new read-only AI Standup Agent.
- Graceful offline fallback mechanisms.
- Cross-platform CI matrix supporting Windows and Linux.

---

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

---

## 🌿 Branch Grouping Limitations

When using `--group-by branch`, Git Standup Bot groups commits by their active branch tip decorations (retrieved using `%D` format in `git log`).

> [!NOTE]
> **Git limitation:** Git is content-addressable and commit-history is a directed acyclic graph. Commits do not store the name of the branch they were originally committed to.
> Therefore, once branches are merged, or if commits are historical parents, direct branch ref decorations are not present. Undecorated historical commits will default to the currently checked-out branch at runtime.

---

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

---

## 📄 License

MIT — see [LICENSE](LICENSE)
