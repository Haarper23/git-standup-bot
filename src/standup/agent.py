"""Developer Agent module — analyzes git activity to provide technical lead insights.

Provides risk assessment, security/quality feedback, and next action items.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from standup.git_parser import Commit
from standup.ai_summarizer import get_local_ollama_models, select_best_ollama_model, summarize_ollama, summarize_openai, summarize_gemini


# System prompt that forces the LLM to act as a Tech Lead Agent and return structured JSON
AGENT_SYSTEM_PROMPT = """You are a Senior Tech Lead AI Agent. Analyze the given list of git commits 
and provide an engineering-level assessment of the work done.

You MUST respond ONLY with a valid JSON object matching the following structure:
{
  "risk_level": "High | Medium | Low",
  "impact_summary": "Short 1-sentence summary of the architectural impact.",
  "security_code_quality": [
    "Security or code quality note 1",
    "Security or code quality note 2"
  ],
  "recommended_next_steps": [
    "Actionable TODO item 1 (e.g. add unit tests for X)",
    "Actionable TODO item 2 (e.g. document API parameters for Y)"
  ]
}

Rules:
- Be critical and constructive.
- Identify potential missing pieces (e.g. did they add a feature but no tests? did they edit database config?).
- Keep array lists concise (max 3 items per list).
- Do NOT output any conversational text, markdown wrapping (like ```json), or explanations outside the JSON block. Only return raw JSON."""


@dataclass
class AgentAssessment:
    """Structured assessment produced by the Tech Lead Agent."""

    risk_level: str = "Low"
    impact_summary: str = "No significant changes."
    security_code_quality: list[str] = field(default_factory=list)
    recommended_next_steps: list[str] = field(default_factory=list)


def _format_commits_for_agent(commits: list[Commit]) -> str:
    """Format commits including subjects and bodies for deep analysis."""
    lines: list[str] = []
    for c in commits:
        body_part = f"\n  Details: {c.body}" if c.body.strip() else ""
        lines.append(f"- [{c.repo_name}] {c.subject}{body_part}")
    return "\n".join(lines)


def run_developer_agent(
    commits: list[Commit],
    provider: str = "auto",
    api_key: str | None = None,
    openai_model: str = "gpt-4o-mini",
    ollama_model: str = "llama3.1",
    ollama_url: str = "http://localhost:11434",
    gemini_model: str = "gemini-2.5-flash",
    gemini_api_key: str | None = None,
) -> AgentAssessment:
    """Run the autonomous Tech Lead Agent to analyze commits and return structured insights.

    Args:
        commits: List of commits to analyze.
        provider: "auto", "openai", "ollama", or "gemini".
        api_key: OpenAI API key.
        openai_model: OpenAI model name.
        ollama_model: Ollama model name.
        ollama_url: Ollama server URL.
        gemini_model: Gemini model name.
        gemini_api_key: Gemini API key.

    Returns:
        Populated AgentAssessment object.
    """
    if not commits:
        return AgentAssessment()

    # Resolve provider
    resolved_provider = provider.lower()
    ollama_models = get_local_ollama_models(ollama_url)
    is_ollama_online = len(ollama_models) > 0

    if resolved_provider == "auto":
        if is_ollama_online:
            resolved_provider = "ollama"
        elif gemini_api_key:
            resolved_provider = "gemini"
        elif api_key:
            resolved_provider = "openai"
        else:
            return AgentAssessment(
                risk_level="Unknown",
                impact_summary="Agent offline. No AI backend (Ollama, Gemini, OpenAI) could be reached."
            )

    commit_text = _format_commits_for_agent(commits)
    user_prompt = f"Analyze these commits and return the JSON assessment:\n\n{commit_text}"

    raw_response: str | None = None

    # Call the appropriate LLM with custom system prompt overrides if possible
    # We reuse existing functions but we need to inject the custom agent system prompt.
    # To keep code clean and dry, we temporarily override the system prompt or call directly.
    try:
        if resolved_provider == "ollama":
            selected_model = select_best_ollama_model(ollama_models, ollama_model)
            # Custom JSON generation payload for Ollama
            import urllib.request
            payload = json.dumps({
                "model": selected_model,
                "prompt": f"{AGENT_SYSTEM_PROMPT}\n\n{user_prompt}",
                "stream": False,
                "format": "json",  # Forces JSON output
                "options": {"temperature": 0.2},
            }).encode("utf-8")
            
            # Safe call
            req = urllib.request.Request(
                f"{ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=45) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                raw_response = data.get("response")

        elif resolved_provider == "gemini":
            # Gemini raw content call with system instruction
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": f"{AGENT_SYSTEM_PROMPT}\n\n{user_prompt}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"  # Forces JSON output
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                raw_response = data["candidates"][0]["content"]["parts"][0]["text"]

        elif resolved_provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},  # Forces JSON output
                temperature=0.2,
            )
            raw_response = response.choices[0].message.content

    except Exception as e:
        return AgentAssessment(
            risk_level="Error",
            impact_summary=f"Failed to communicate with AI provider ({resolved_provider}). Details: {e}"
        )

    if not raw_response:
        return AgentAssessment(
            risk_level="Error",
            impact_summary="Empty response from AI provider."
        )

    # Parse JSON safely
    try:
        # Clean markdown wrappers if any LLM ignored the prompt rules
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        parsed = json.loads(clean_json)
        return AgentAssessment(
            risk_level=parsed.get("risk_level", "Low"),
            impact_summary=parsed.get("impact_summary", ""),
            security_code_quality=parsed.get("security_code_quality", []),
            recommended_next_steps=parsed.get("recommended_next_steps", [])
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        # Fallback parsing for unstructured responses
        return AgentAssessment(
            risk_level="Medium",
            impact_summary="Failed to parse structured agent analysis. Raw output:\n" + raw_response[:300]
        )
