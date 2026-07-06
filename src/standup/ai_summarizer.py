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

    # Validate URL scheme to prevent file:// and other unexpected protocol handlers
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        return None

    try:
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def summarize_gemini(
    commits: list[Commit],
    model: str = "gemini-2.5-flash",
    api_key: str | None = None,
) -> str | None:
    """Generate a standup summary using Google Gemini REST API.

    Args:
        commits: List of commits to summarize.
        model: Gemini model name.
        api_key: Gemini API key. Required.

    Returns:
        AI-generated summary string, or None if failed.
    """
    if not api_key or not commits:
        return None

    commit_text = _format_commits_for_prompt(commits)
    prompt = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT_TEMPLATE.format(commits=commit_text)}"

    # Google Gemini REST API payload structure
    payload = json.dumps({
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }).encode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Validate URL scheme to prevent file:// and other unexpected protocol handlers
    if not url.startswith("https://"):
        return None

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            # Extracts text from response: data['candidates'][0]['content']['parts'][0]['text']
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def get_local_ollama_models(base_url: str = "http://localhost:11434") -> list[str]:
    """Fetch installed models from local Ollama instance.

    Returns:
        List of installed model names, or empty list if offline.
    """
    if not (base_url.startswith("http://") or base_url.startswith("https://")):
        return []

    try:
        req = urllib.request.Request(
            f"{base_url}/api/tags",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def select_best_ollama_model(installed_models: list[str], configured_model: str) -> str:
    """Select the best available model from installed Ollama models.

    Args:
        installed_models: List of model names returned by Ollama.
        configured_model: Default configured model.

    Returns:
        Best model name.
    """
    if not installed_models:
        return configured_model

    # Check if configured model is installed (exact or tag mismatch)
    for model in installed_models:
        if model == configured_model or model.split(":")[0] == configured_model.split(":")[0]:
            return model

    # Priority list based on common/popular models in user settings
    priority_keywords = [
        "deepseek-r1",
        "gemma4",
        "llama3.1",
        "qwen3.6",
        "qwen3",
        "llama3",
        "mistral",
        "gemma",
    ]

    for keyword in priority_keywords:
        for model in installed_models:
            # Check if keyword is in the model name (e.g. 'deepseek-r1:8b')
            if keyword in model.lower():
                return model

    # Fallback to the first installed model
    return installed_models[0]


def generate_summary(
    commits: list[Commit],
    provider: str = "auto",
    api_key: str | None = None,
    openai_model: str = "gpt-4o-mini",
    ollama_model: str = "llama3.1",
    ollama_url: str = "http://localhost:11434",
    gemini_model: str = "gemini-2.5-flash",
    gemini_api_key: str | None = None,
) -> str | None:
    """Generate an AI summary using the configured provider.

    Tries the specified provider first. If provider is "auto",
    automatically detects the best available provider in order:
    Ollama (if online) -> Gemini (if key set) -> OpenAI (if key set).

    Args:
        commits: List of commits to summarize.
        provider: "auto", "openai", "ollama", or "gemini".
        api_key: OpenAI API key.
        openai_model: OpenAI model name.
        ollama_model: Ollama model name.
        ollama_url: Ollama server URL.
        gemini_model: Gemini model name.
        gemini_api_key: Gemini API key.

    Returns:
        Summary string or None.
    """
    if not commits:
        return None

    resolved_provider = provider.lower()
    ollama_models = get_local_ollama_models(ollama_url)
    is_ollama_online = len(ollama_models) > 0

    # Auto-detection routing
    if resolved_provider == "auto":
        if is_ollama_online:
            resolved_provider = "ollama"
        elif gemini_api_key:
            resolved_provider = "gemini"
        elif api_key:
            resolved_provider = "openai"
        else:
            # No provider available
            return None

    # Run the resolved provider
    if resolved_provider == "ollama":
        # Automatically select the best installed model
        selected_model = select_best_ollama_model(ollama_models, ollama_model)
        return summarize_ollama(commits, model=selected_model, base_url=ollama_url)
    elif resolved_provider == "gemini":
        return summarize_gemini(commits, model=gemini_model, api_key=gemini_api_key)
    elif resolved_provider == "openai":
        return summarize_openai(commits, model=openai_model, api_key=api_key)

    return None
