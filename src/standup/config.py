"""Configuration loader for Git Standup Bot.

Reads settings from .standup.toml, environment variables, and CLI defaults.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


CONFIG_FILENAME = ".standup.toml"

# Search order: current dir → home dir
SEARCH_PATHS = [
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / CONFIG_FILENAME,
]

SUPPORTED_PROVIDERS = frozenset({"auto", "openai", "gemini", "ollama"})


class InvalidProviderError(Exception):
    """Raised when an invalid provider is configured or supplied."""


def validate_provider(provider_val: any) -> str:
    """Validates and normalizes the provider value, raising InvalidProviderError on failure."""
    if not isinstance(provider_val, str):
        raise InvalidProviderError(
            f"Invalid provider {repr(provider_val)}. Expected one of: auto, gemini, ollama, openai."
        )
    normalized = provider_val.strip().lower()
    if not normalized or normalized not in SUPPORTED_PROVIDERS:
        raise InvalidProviderError(
            f"Invalid provider '{provider_val}'. Expected one of: auto, gemini, ollama, openai."
        )
    return normalized


@dataclass
class AIConfig:
    """AI summarization settings."""

    enabled: bool = False
    provider: str = "auto"  # "auto", "openai", "ollama", or "gemini"
    openai_model: str = "gpt-4o-mini"
    ollama_model: str = "llama3.1"
    ollama_url: str = "http://localhost:11434"
    gemini_model: str = "gemini-2.5-flash"

    @property
    def api_key(self) -> str | None:
        """Get OpenAI API key from environment."""
        return os.environ.get("OPENAI_API_KEY")

    @property
    def gemini_api_key(self) -> str | None:
        """Get Gemini API key from environment."""
        return os.environ.get("GEMINI_API_KEY")


@dataclass
class OutputConfig:
    """Output formatting settings."""

    export_path: str = ""
    show_hashes: bool = False
    group_by: str = "type"  # "type", "branch", or "repo"


@dataclass
class Config:
    """Complete application configuration."""

    author: str = ""
    since: str = "yesterday"
    timezone: str = "UTC"
    repo_paths: list[str] = field(default_factory=list)
    standup_agent: bool = False
    ai: AIConfig = field(default_factory=AIConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


def find_config_file() -> Path | None:
    """Find the first existing config file in search paths."""
    for path in SEARCH_PATHS:
        if path.is_file():
            return path
    return None


def load_config(config_path: Path | None = None) -> Config:
    """Load configuration from TOML file with environment variable overrides.

    Args:
        config_path: Explicit path to config file. If None, searches default locations.

    Returns:
        Populated Config instance.
    """
    config = Config()

    # Find and load TOML file
    path = config_path or find_config_file()
    if path and path.is_file():
        with open(path, "rb") as f:
            data = tomllib.load(f)

        # General settings
        general = data.get("general", {})
        config.author = general.get("author", config.author)
        config.since = general.get("since", config.since)
        config.timezone = general.get("timezone", config.timezone)
        config.standup_agent = general.get("standup_agent", config.standup_agent)

        # Repo paths
        repos = data.get("repos", {})
        paths = repos.get("paths", [])
        config.repo_paths = [str(Path(p).expanduser()) for p in paths if p]

        # AI settings
        ai_data = data.get("ai", {})
        config.ai = AIConfig(
            enabled=ai_data.get("enabled", False),
            provider=ai_data.get("provider", "auto"),
            openai_model=ai_data.get("openai_model", "gpt-4o-mini"),
            ollama_model=ai_data.get("ollama_model", "llama3.1"),
            ollama_url=ai_data.get("ollama_url", "http://localhost:11434"),
            gemini_model=ai_data.get("gemini_model", "gemini-2.5-flash"),
        )

        # Output settings
        out_data = data.get("output", {})
        config.output = OutputConfig(
            export_path=out_data.get("export_path", ""),
            show_hashes=out_data.get("show_hashes", False),
            group_by=out_data.get("group_by", "type"),
        )

    # Environment variable overrides
    if os.environ.get("STANDUP_AUTHOR"):
        config.author = os.environ["STANDUP_AUTHOR"]
    if os.environ.get("STANDUP_AI_PROVIDER"):
        config.ai.provider = os.environ["STANDUP_AI_PROVIDER"]
    if os.environ.get("STANDUP_AGENT"):
        config.standup_agent = os.environ["STANDUP_AGENT"].lower() in ("true", "1", "yes")

    # Validate and normalize resolved provider
    config.ai.provider = validate_provider(config.ai.provider)

    return config
