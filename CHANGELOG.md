# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

Development changes and unreleased features will be tracked in this section prior to version tagging.

## [1.0.0] - 2026-07-07

### Added
- Git activity parsing and repository grouping
- Categorized terminal reports
- Markdown export
- Deterministic daily standup reports
- Timezone-aware date handling
- Tech Lead AI Agent
- AI Standup Agent with four structured sections
- OpenAI, Gemini, Ollama, and auto provider routing
- Local Ollama model discovery
- Deterministic offline fallback
- Provider validation
- Bounded provider requests and responses
- Windows-safe terminal encoding
- GitHub Actions matrix

### Security
- Read-only AI Standup Agent boundary
- No shell execution
- No Git writes
- No model-provided path access
- Strict provider-envelope and model-output validation
- Bounded commit context and prompt sizes

### Fixed
- Windows encoding reliability
- Repository-root parsing and deduplication
- Timezone compatibility
- Python 3.10 TOML test compatibility
- Controlled provider/network failures
