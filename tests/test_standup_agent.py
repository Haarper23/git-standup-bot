"""Unit and integration tests for the AI Standup Agent."""

import json
import os
import sys
import socket
import urllib.error
import urllib.request
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

from standup.git_parser import Commit
from standup.grouper import RepoGroup, CommitGroup
from standup.config import (
    Config,
    load_config,
    InvalidProviderError,
    validate_provider,
)
from standup.standup_agent import (
    StandupAssessment,
    get_deterministic_fallback,
    run_standup_agent,
    _build_bounded_commit_context,
    _discover_ollama_models,
    MAX_COMMITS,
    MAX_SUBJECT_LEN,
    MAX_CONTEXT_BYTES,
    MAX_PROMPT_BYTES,
    MAX_RESPONSE_LEN,
    MAX_ENTRIES_PER_SECTION,
    MAX_ENTRY_LEN,
    StandupAgentError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from standup.formatter import render_markdown, render_terminal
from standup.cli import main


def _commit(subject: str, repo: str = "test-repo") -> Commit:
    """Helper to create a Commit object."""
    return Commit(
        hash="1234567890abcdef",
        author="Test User",
        date=datetime(2026, 7, 6, 12, 0, 0),
        subject=subject,
        body="This is an implementation detail body.",
        branch="main",
        repo_name=repo,
    )


# ---------------------------------------------------------------------------
# 1 — Central Provider Validation Tests
# ---------------------------------------------------------------------------

def test_validate_provider_valid_values():
    """Verify valid supported providers normalize correctly."""
    assert validate_provider("auto") == "auto"
    assert validate_provider("  openai  ") == "openai"
    assert validate_provider("GeMiNi") == "gemini"
    assert validate_provider("ollama") == "ollama"


def test_validate_provider_invalid_values():
    """Verify invalid provider throws InvalidProviderError."""
    with pytest.raises(InvalidProviderError):
        validate_provider("bogus")
    with pytest.raises(InvalidProviderError):
        validate_provider("")
    with pytest.raises(InvalidProviderError):
        validate_provider(None)
    with pytest.raises(InvalidProviderError):
        validate_provider(123)


def test_config_without_provider_still_loads():
    """Verify config without a provider block falls back to default auto provider."""
    # Mock loaded dict missing ai.provider
    with patch("tomllib.load", return_value={"general": {"author": "Test"}}), \
         patch("builtins.open", MagicMock()):
        cfg = load_config(Path(".standup.toml"))
        assert cfg.ai.provider == "auto"


def test_cli_rejects_invalid_provider_cleanly():
    """Verify CLI exits non-zero and prints concise error for invalid provider."""
    runner = CliRunner()
    result = runner.invoke(main, ["--provider", "bogus"])
    assert result.exit_code != 0
    assert "Error: Invalid value for '--provider'" in result.output
    assert "Traceback" not in result.output


def test_cli_bogus_config_provider_rejected():
    """Verify invalid provider in TOML config exits cleanly."""
    with patch("standup.cli.load_config", side_effect=InvalidProviderError("Invalid provider 'bogus'")):
        runner = CliRunner()
        result = runner.invoke(main, [])
        assert result.exit_code != 0
        assert "Traceback" not in result.output


# ---------------------------------------------------------------------------
# 2 — Network OSError/ConnectionError Fallback Tests
# ---------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, data: bytes):
        self.data = data
        self.read_calls = []

    def read(self, amt: int = -1):
        self.read_calls.append(amt)
        if amt == -1:
            return self.data
        return self.data[:amt]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class ErrorResponse:
    def __init__(self, exception_to_raise):
        self.exception_to_raise = exception_to_raise

    def read(self, amt: int = -1):
        raise self.exception_to_raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def test_ollama_urlopen_oserror_falls_back():
    """Ollama urlopen throwing OSError triggers controlled fallback."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("urllib.request.urlopen", side_effect=OSError("Network down")):

        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning


def test_ollama_urlopen_connectionerror_falls_back():
    """Ollama urlopen throwing ConnectionError triggers controlled fallback."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("urllib.request.urlopen", side_effect=ConnectionError("Connection refused")):

        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning


def test_ollama_response_read_oserror_falls_back():
    """Ollama response read throwing OSError triggers controlled fallback."""
    fake_err_resp = ErrorResponse(OSError("Read timed out"))
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("urllib.request.urlopen", return_value=fake_err_resp):

        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning


def test_gemini_urlopen_oserror_falls_back():
    """Gemini urlopen throwing OSError triggers controlled fallback."""
    with patch("urllib.request.urlopen", side_effect=OSError("Network down")):
        assessment = run_standup_agent([_commit("feat: test")], provider="gemini", gemini_api_key="gemini-key")
        assert "Failed to parse or communicate" in assessment.warning


def test_gemini_urlopen_connectionerror_falls_back():
    """Gemini urlopen throwing ConnectionError triggers controlled fallback."""
    with patch("urllib.request.urlopen", side_effect=ConnectionError("Connection refused")):
        assessment = run_standup_agent([_commit("feat: test")], provider="gemini", gemini_api_key="gemini-key")
        assert "Failed to parse or communicate" in assessment.warning


def test_gemini_response_read_oserror_falls_back():
    """Gemini response read throwing OSError triggers controlled fallback."""
    fake_err_resp = ErrorResponse(OSError("Read timed out"))
    with patch("urllib.request.urlopen", return_value=fake_err_resp):
        assessment = run_standup_agent([_commit("feat: test")], provider="gemini", gemini_api_key="gemini-key")
        assert "Failed to parse or communicate" in assessment.warning


def test_existing_timeout_and_urlerror_still_fallback():
    """Verify that TimeoutError and URLError are caught and routed to fallback."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("urllib.request.urlopen", side_effect=TimeoutError("Timeout")):

        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning

    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Offline")):

        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning


# ---------------------------------------------------------------------------
# 3 — Strict Direct Ollama Discovery Tests
# ---------------------------------------------------------------------------

def test_ollama_discovery_valid_response():
    """Ollama discovery successfully parses valid payload."""
    valid_payload = {
        "models": [
            {"name": "llama3.1:latest"},
            {"name": "gemma2"}
        ]
    }
    fake_resp = FakeResponse(json.dumps(valid_payload).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        models = _discover_ollama_models("http://localhost:11434")
        assert models == ["llama3.1:latest", "gemma2"]


def test_ollama_discovery_missing_models():
    """Ollama discovery throws ProviderResponseError when 'models' is missing."""
    fake_resp = FakeResponse(json.dumps({"other": "field"}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_models_not_list():
    """Ollama discovery throws ProviderResponseError when 'models' is not a list."""
    fake_resp = FakeResponse(json.dumps({"models": "string"}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_empty_models_list():
    """Ollama discovery handles empty models list gracefully by returning empty list."""
    fake_resp = FakeResponse(json.dumps({"models": []}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        models = _discover_ollama_models("http://localhost:11434")
        assert models == []


def test_ollama_discovery_model_entry_not_dict():
    """Ollama discovery throws when model entry is not a dict."""
    fake_resp = FakeResponse(json.dumps({"models": ["string"]}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_missing_model_name():
    """Ollama discovery throws when model entry is missing 'name'."""
    fake_resp = FakeResponse(json.dumps({"models": [{"size": 123}]}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_model_name_not_string():
    """Ollama discovery throws when model name is not a string."""
    fake_resp = FakeResponse(json.dumps({"models": [{"name": 123}]}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_malformed_entries_fallback():
    """Verify malformed models entry list causes controlled fallback in run_standup_agent."""
    fake_resp = FakeResponse(json.dumps({"models": [{}]}).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning


def test_ollama_discovery_oserror_falls_back():
    """Ollama discovery throwing OSError triggers controlled fallback."""
    with patch("urllib.request.urlopen", side_effect=OSError("Access denied")):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_connectionerror_falls_back():
    """Ollama discovery throwing ConnectionError triggers controlled fallback."""
    with patch("urllib.request.urlopen", side_effect=ConnectionError("Refused")):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_timeout_falls_back():
    """Ollama discovery throwing TimeoutError triggers controlled fallback."""
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Timed out")):
        with pytest.raises(ProviderUnavailableError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_type_error_propagates():
    """TypeError from discovery helper propagates."""
    with patch("urllib.request.urlopen", side_effect=TypeError("Bad arg")):
        with pytest.raises(TypeError):
            _discover_ollama_models("http://localhost:11434")


def test_ollama_discovery_attribute_error_propagates():
    """AttributeError from discovery helper propagates."""
    with patch("urllib.request.urlopen", side_effect=AttributeError("Bad attr")):
        with pytest.raises(AttributeError):
            _discover_ollama_models("http://localhost:11434")


def test_no_call_reaches_broad_ai_summarizer_discovery():
    """Verify that Standup Agent discovery no longer imports/calls get_local_ollama_models."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("standup.ai_summarizer.get_local_ollama_models") as mock_summarizer_discovery:

        run_standup_agent([_commit("feat: test")], provider="ollama")
        assert not mock_summarizer_discovery.called


# ---------------------------------------------------------------------------
# 4 — Gemini Response Wrapper Structure Validation
# ---------------------------------------------------------------------------

def _verify_gemini_wrapper(payload_dict):
    """Helper to mock Gemini API returning a JSON payload dict."""
    fake_resp = FakeResponse(json.dumps(payload_dict).encode("utf-8"))
    with patch("urllib.request.urlopen", return_value=fake_resp):
        assessment = run_standup_agent([_commit("feat: test")], provider="gemini", gemini_api_key="gemini-key")
        return assessment


def test_gemini_wrapper_missing_candidates():
    """Gemini response missing candidates."""
    assessment = _verify_gemini_wrapper({"other": []})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_candidates_not_list():
    """Gemini response candidates field is not a list."""
    assessment = _verify_gemini_wrapper({"candidates": "string"})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_candidates_empty():
    """Gemini response candidates list is empty."""
    assessment = _verify_gemini_wrapper({"candidates": []})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_candidate_not_object():
    """Gemini candidate is not an object."""
    assessment = _verify_gemini_wrapper({"candidates": ["string"]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_missing_content():
    """Gemini candidate content field is missing."""
    assessment = _verify_gemini_wrapper({"candidates": [{}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_content_not_object():
    """Gemini candidate content is not an object."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": "string"}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_missing_parts():
    """Gemini parts list is missing."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_parts_not_list():
    """Gemini parts is not a list."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {"parts": "string"}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_parts_empty():
    """Gemini parts is empty."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {"parts": []}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_part_not_object():
    """Gemini part is not an object."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {"parts": ["string"]}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_missing_text():
    """Gemini text field is missing from part."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {"parts": [{}]}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_text_not_string():
    """Gemini text is not a string."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {"parts": [{"text": 123}]}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_text_empty():
    """Gemini text is empty after trimming."""
    assessment = _verify_gemini_wrapper({"candidates": [{"content": {"parts": [{"text": "   "}]}}]})
    assert "Failed to parse or communicate" in assessment.warning


def test_gemini_wrapper_valid_succeeds():
    """Valid Gemini response succeeds."""
    inner_assessment = {
        "completed": ["Task Done"],
        "in_progress": ["WIP Task"],
        "risks_blockers": ["Blocker Task"],
        "next_steps": ["Next Step Task"]
    }
    payload = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps(inner_assessment)
                }]
            }
        }]
    }
    assessment = _verify_gemini_wrapper(payload)
    assert assessment.completed == ["Task Done"]
    assert assessment.warning is None


# ---------------------------------------------------------------------------
# 5 — UTF-8 Byte Bounding Context and Prompt Tests
# ---------------------------------------------------------------------------

def test_byte_bounding_ascii_subjects():
    """Verify context bounding under ASCII characters behaves predictably."""
    commits = [_commit(f"feat: subject {i}") for i in range(10)]
    serialized = _build_bounded_commit_context(commits)
    assert len(serialized.encode("utf-8")) <= MAX_CONTEXT_BYTES
    assert json.loads(serialized)


def test_byte_bounding_turkish_characters():
    """Verify Turkish characters (multi-byte UTF-8 characters) are bounded accurately by byte size."""
    turkish_subject = "feat: " + ("şığöçŞİĞÖÇ" * 30)
    commits = [_commit(turkish_subject) for _ in range(50)]

    serialized = _build_bounded_commit_context(commits)
    serialized_bytes = serialized.encode("utf-8")
    assert len(serialized_bytes) <= MAX_CONTEXT_BYTES
    parsed = json.loads(serialized)
    assert parsed[0]["commit_message"].startswith("feat: şığöç")


def test_byte_bounding_emoji_heavy_subjects():
    """Verify Emoji characters (4 bytes each in UTF-8) are measured and bounded accurately by bytes."""
    emoji_subject = "feat: " + ("🚀🤖🔥" * 30)
    commits = [_commit(emoji_subject) for _ in range(50)]

    serialized = _build_bounded_commit_context(commits)
    serialized_bytes = serialized.encode("utf-8")
    assert len(serialized_bytes) <= MAX_CONTEXT_BYTES
    parsed = json.loads(serialized)
    assert parsed[0]["commit_message"].startswith("feat: 🚀🤖🔥")


def test_byte_bounding_escaped_quotes_and_backslashes():
    """Verify escaped quotes and backslashes inside context are encoded and remain valid JSON."""
    c = _commit('feat: subject with "quotes" and \\backslashes\\')
    serialized = _build_bounded_commit_context([c])
    assert len(serialized.encode("utf-8")) <= MAX_CONTEXT_BYTES
    parsed = json.loads(serialized)
    assert parsed[0]["commit_message"] == 'feat: subject with "quotes" and \\backslashes\\'


def test_byte_bounding_record_omitted_completely_when_over_limit():
    """A commit record that would exceed the remaining byte budget is omitted completely (no slicing)."""
    large_commits = [_commit("feat: " + ("x" * 450), repo=f"repo-{i}") for i in range(40)]
    serialized = _build_bounded_commit_context(large_commits)
    serialized_bytes = serialized.encode("utf-8")

    assert len(serialized_bytes) <= MAX_CONTEXT_BYTES
    parsed = json.loads(serialized)
    assert len(parsed) < 40
    for item in parsed:
        assert item["repository"].startswith("repo-")


def test_byte_bounding_max_commits_enforced():
    """Verify that MAX_COMMITS limit still restricts context generation even if budget is unused."""
    small_commits = [_commit("feat: c") for i in range(MAX_COMMITS + 20)]
    serialized = _build_bounded_commit_context(small_commits)
    parsed = json.loads(serialized)
    assert len(parsed) == MAX_COMMITS


def test_prompt_size_exceeds_max_prompt_bytes():
    """Verify prompt is rejected if the final complete prompt exceeds MAX_PROMPT_BYTES."""
    commits = [_commit("feat: " + ("x" * 290)) for _ in range(50)]
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("standup.standup_agent.MAX_PROMPT_BYTES", 1000):

        assessment = run_standup_agent(commits, provider="ollama")
        assert "Failed to parse or communicate" in assessment.warning


# ---------------------------------------------------------------------------
# 6 — Legacy Risk, Command, and Formatting Tests
# ---------------------------------------------------------------------------

def test_risk_classification_false_positives():
    """Verify that documentation or testing context keywords do NOT trigger blocker classification."""
    false_positives = [
        "docs: rollback strategy overview",
        "docs: rollback documentation",
        "test: regression testing guide",
        "docs: regression prevention techniques",
        "feat: security dashboard",
        "docs: update security documentation",
        "feat: revertable operation support",
        "docs: breaking-change policy",
        "test: vulnerability scanner fixture",
    ]
    for subj in false_positives:
        c = _commit(subj)
        assessment = get_deterministic_fallback([c])
        assert assessment.risks_blockers == ["No explicit blockers detected from commit messages."]
        assert assessment.next_steps == ["Review the current branch and select the next planned task."]


def test_risk_classification_true_positives():
    """Verify that explicit blocker prefix and action/state phrases are correctly classified as risks."""
    true_positives = [
        "blocker: provider unavailable",
        "blocked by invalid configuration",
        "breaking change: rename output field",
        "vulnerability in parser",
        "rollback: provider update",
        "rollback provider update",
        "revert: unsafe provider change",
        "reverted unsafe provider change",
        "failed migration",
        "regression in formatter",
        "security vulnerability in parser",
        "security: unsafe response parsing",
    ]
    for subj in true_positives:
        c = _commit(subj)
        assessment = get_deterministic_fallback([c])
        assert c.clean_subject[:MAX_ENTRY_LEN] in assessment.risks_blockers
        assert assessment.completed == ["No normal completed commits."]


def test_assertion_error_propagates():
    """Programming defects (AssertionError) propagate and are not swallowed."""
    with patch("standup.standup_agent._discover_ollama_models", side_effect=AssertionError("Assert Error")):
        with pytest.raises(AssertionError, match="Assert Error"):
            run_standup_agent([_commit("feat: test")], provider="auto")


def test_type_error_propagates():
    """Programming defects (TypeError) propagate and are not swallowed."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("standup.standup_agent._build_bounded_commit_context", side_effect=TypeError("Type error")):
        with pytest.raises(TypeError):
            run_standup_agent([_commit("feat: test")], provider="ollama")


def test_attribute_error_propagates():
    """Programming defects (AttributeError) propagate and are not swallowed."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("standup.standup_agent._build_bounded_commit_context", side_effect=AttributeError("Attribute error")):
        with pytest.raises(AttributeError):
            run_standup_agent([_commit("feat: test")], provider="ollama")


def test_keyboard_interrupt_propagates():
    """System-level interruptions (KeyboardInterrupt) propagate."""
    with patch("standup.standup_agent._discover_ollama_models", side_effect=KeyboardInterrupt()):
        with pytest.raises(KeyboardInterrupt):
            run_standup_agent([_commit("feat: test")], provider="auto")


def test_explicit_openai_never_calls_ollama():
    """Explicit openai provider routing never calls Ollama or Gemini APIs."""
    with patch("standup.standup_agent._discover_ollama_models") as mock_ollama, \
         patch("openai.OpenAI") as mock_openai:

        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_comp = MagicMock()
        mock_comp.choices = [MagicMock()]
        mock_comp.choices[0].message.content = '{"completed": [], "in_progress": [], "risks_blockers": [], "next_steps": []}'
        mock_client.chat.completions.create.return_value = mock_comp

        assessment = run_standup_agent([_commit("feat: test")], provider="openai", api_key="test-key")
        assert not mock_ollama.called
        assert mock_client.chat.completions.create.called
        assert assessment.warning is None


def test_explicit_gemini_never_calls_ollama():
    """Explicit gemini provider routing never calls Ollama or OpenAI APIs."""
    fake_gemini_resp = FakeResponse(json.dumps({
        "candidates": [{"content": {"parts": [{"text": '{"completed": [], "in_progress": [], "risks_blockers": [], "next_steps": []}'}]}}]
    }).encode("utf-8"))

    with patch("standup.standup_agent._discover_ollama_models") as mock_ollama, \
         patch("urllib.request.urlopen", return_value=fake_gemini_resp) as mock_url, \
         patch("openai.OpenAI") as mock_openai:

        assessment = run_standup_agent([_commit("feat: test")], provider="gemini", gemini_api_key="test-key")
        assert not mock_ollama.called
        assert not mock_openai.called
        assert mock_url.called
        assert assessment.warning is None


def test_explicit_ollama_never_calls_gemini():
    """Explicit ollama provider routing never calls Gemini URL or OpenAI client."""
    fake_ollama_resp = FakeResponse(json.dumps({
        "response": '{"completed": [], "in_progress": [], "risks_blockers": [], "next_steps": []}'
    }).encode("utf-8"))

    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]), \
         patch("urllib.request.urlopen", return_value=fake_ollama_resp) as mock_url, \
         patch("openai.OpenAI") as mock_openai:

        assessment = run_standup_agent([_commit("feat: test")], provider="ollama")
        assert not mock_openai.called

        request_obj = mock_url.call_args[0][0]
        assert "localhost:11434" in request_obj.full_url
        assert "googleapis.com" not in request_obj.full_url


def test_auto_provider_discovery_routing():
    """Auto provider resolution executes auto-detection routing priority order."""
    with patch("standup.standup_agent._discover_ollama_models", return_value=["llama3.1"]) as mock_probe, \
         patch("urllib.request.urlopen") as mock_url:

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "{}"}).encode("utf-8")
        mock_url.return_value.__enter__.return_value = mock_response

        run_standup_agent([_commit("feat: test")], provider="auto")
        assert mock_probe.called

    fake_gemini_resp = FakeResponse(json.dumps({
        "candidates": [{"content": {"parts": [{"text": '{"completed": [], "in_progress": [], "risks_blockers": [], "next_steps": []}'}]}}]
    }).encode("utf-8"))
    with patch("standup.standup_agent._discover_ollama_models", return_value=[]), \
         patch("urllib.request.urlopen", return_value=fake_gemini_resp) as mock_url:

        run_standup_agent([_commit("feat: test")], provider="auto", gemini_api_key="gemini-key")
        request_obj = mock_url.call_args[0][0]
        request_url = request_obj.full_url
        assert "generativelanguage.googleapis.com" in request_url


def test_standup_agent_appears_in_help():
    """--standup-agent appears in help."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--standup-agent" in result.output
    assert "--no-standup-agent" in result.output


def test_standup_agent_produces_four_terminal_sections():
    """--standup-agent produces the four terminal sections."""
    assessment = StandupAssessment(
        completed=["Completed A"],
        in_progress=["In Progress B"],
        risks_blockers=["Blocker C"],
        next_steps=["Next D"]
    )

    with patch("standup.formatter.Console.print") as mock_print:
        render_terminal([], standup_assessment=assessment)

        content_found = []
        for call in mock_print.call_args_list:
            if len(call[0]) > 0:
                arg = call[0][0]
                if hasattr(arg, "renderable"):
                    content_found.append(str(arg.renderable))
                else:
                    content_found.append(str(arg))

        all_printed = " ".join(content_found)
        assert "AI Standup Agent" in all_printed
        assert "Completed" in all_printed
        assert "In Progress" in all_printed
        assert "Risks / Blockers" in all_printed
        assert "Next Steps" in all_printed


def test_markdown_export_includes_all_four_sections():
    """Markdown export includes all four sections."""
    assessment = StandupAssessment(
        completed=["Completed A"],
        in_progress=["In Progress B"],
        risks_blockers=["Blocker C"],
        next_steps=["Next D"]
    )
    md = render_markdown([], standup_assessment=assessment)
    assert "## 🤖 AI Standup Agent" in md
    assert "### Completed" in md
    assert "### In Progress" in md
    assert "### Risks / Blockers" in md
    assert "### Next Steps" in md
    assert "- Completed A" in md


def test_no_ai_with_standup_agent_uses_deterministic_fallback():
    """--no-ai with --standup-agent uses deterministic fallback."""
    runner = CliRunner()
    with patch("standup.cli.parse_commits", return_value=[_commit("feat: check no-ai fallback")]), \
         patch("standup.cli.run_standup_agent") as mock_run_agent:

        result = runner.invoke(main, ["--standup-agent", "--no-ai"])
        assert result.exit_code == 0
        assert not mock_run_agent.called
        assert "check no-ai fallback" in result.output


def test_existing_agent_behavior_remains_unchanged():
    """Existing --agent behavior remains unchanged."""
    runner = CliRunner()
    with patch("standup.cli.parse_commits", return_value=[_commit("feat: check agent")]), \
         patch("standup.cli.run_developer_agent") as mock_run_dev_agent:

        runner.invoke(main, ["--agent"])
        assert mock_run_dev_agent.called


def test_existing_cli_commands_backward_compatible():
    """Existing CLI commands remain backward compatible."""
    runner = CliRunner()
    with patch("standup.cli.parse_commits", return_value=[_commit("feat: normal CLI run")]):
        result = runner.invoke(main, [])
        assert result.exit_code == 0
        assert "normal CLI run" in result.output
        assert "AI Standup Agent" not in result.output


def test_cp1254_output_does_not_crash():
    """CP1254 output does not crash with Standup Agent sections."""
    assessment = StandupAssessment(
        completed=["Completed Turkish şığöç"],
        in_progress=["WIP şığöç"],
        risks_blockers=["Blocker şığöç"],
        next_steps=["Next şığöç"]
    )
    md = render_markdown([], standup_assessment=assessment)
    encoded = md.encode("cp1254", errors="replace")
    assert b"Turkish" in encoded
