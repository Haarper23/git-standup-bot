"""AI Summarizer — generates natural-language standup summaries from commits.

Supports OpenAI API and local Ollama. Gracefully degrades when unavailable.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from standup.git_parser import Commit


SYSTEM_PROMPT = """You are a concise standup report assistant. Given a list of git commits, 
write a brief, natural-language summary suitable for a daily standup meeting.

Rules:
- Use first person ("I worked on...", "I fixed...")
- Group related work into 2-4 bullet points
- Keep it under 100 words
- Focus on WHAT was done, not commit details
- Use professional but friendly tone
- Do NOT include commit hashes or timestamps"""

USER_PROMPT_TEMPLATE = """Summarize these git commits for my daily standup:

{commits}"""


def _format_commits_for_prompt(commits: list[Commit]) -> str:
    """Format commits into a readable string for the AI prompt.

    Args:
        commits: List of Commit objects.

    Returns:
        Formatted string of commits.
    """
    lines: list[str] = []
    for c in commits:
        lines.append(f"- [{c.repo_name}] {c.subject}")
    return "\n".join(lines)


def summarize_openai(
    commits: list[Commit],
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> str | None:
    """Generate a standup summary using OpenAI API.

    Args:
        commits: List of commits to summarize.
        model: OpenAI model to use.
        api_key: OpenAI API key. Required.

    Returns:
        AI-generated summary string, or None if failed.
    """
    if not api_key:
        return None

    if not commits:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        commit_text = _format_commits_for_prompt(commits)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(commits=commit_text),
                },
            ],
            temperature=0.3,
            max_tokens=300,
        )

        return response.choices[0].message.content

    except ImportError:
        return None
    except Exception:
        return None


def summarize_ollama(
    commits: list[Commit],
    model: str = "llama3.1",
    base_url: str = "http://localhost:11434",
) -> str | None:
    """Generate a standup summary using local Ollama.

    Args:
        commits: List of commits to summarize.
        model: Ollama model name.
        base_url: Ollama server URL.

    Returns:
        AI-generated summary string, or None if failed.
    """
    if not commits:
        return None

    commit_text = _format_commits_for_prompt(commits)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(commits=commit_text)}"

    payload = json.dumps({
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.3},
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def generate_summary(
    commits: list[Commit],
    provider: str = "openai",
    api_key: str | None = None,
    openai_model: str = "gpt-4o-mini",
    ollama_model: str = "llama3.1",
    ollama_url: str = "http://localhost:11434",
) -> str | None:
    """Generate an AI summary using the configured provider.

    Tries the specified provider first, returns None on failure.
    Never raises exceptions — AI summary is always optional.

    Args:
        commits: List of commits to summarize.
        provider: "openai" or "ollama".
        api_key: OpenAI API key (required for openai provider).
        openai_model: OpenAI model name.
        ollama_model: Ollama model name.
        ollama_url: Ollama server URL.

    Returns:
        Summary string or None.
    """
    if not commits:
        return None

    if provider == "ollama":
        return summarize_ollama(commits, model=ollama_model, base_url=ollama_url)
    else:
        return summarize_openai(commits, model=openai_model, api_key=api_key)
