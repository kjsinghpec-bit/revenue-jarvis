import json
import subprocess
from types import SimpleNamespace

import pytest

from revenue_jarvis.llm import ClaudeCode, Codex, LLMError


def test_claude_tools_and_customizations_are_disabled(monkeypatch):
    seen = []
    def run(cmd, **kwargs):
        seen.extend(cmd)
        return SimpleNamespace(returncode=0, stdout=json.dumps({"result": "{}"}), stderr="")
    monkeypatch.setattr(subprocess, "run", run)
    ClaudeCode().complete("grounding rules", "evidence", 1)
    assert "--tools" in seen and seen[seen.index("--tools") + 1] == ""
    assert "--safe-mode" in seen and "--strict-mcp-config" in seen
    assert "mcp__*" in seen[seen.index("--disallowedTools") + 1]


def test_bad_cli_envelope_is_a_handled_error(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="[]", stderr=""))
    with pytest.raises(LLMError):
        ClaudeCode().complete("rules", "evidence", 1)


def test_missing_cli_is_a_handled_error(monkeypatch):
    def run(*a, **k): raise FileNotFoundError("missing executable")
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(LLMError):
        ClaudeCode().complete("rules", "evidence", 1)


def test_cli_auth_error_uses_result_instead_of_truncated_metadata(monkeypatch):
    envelope = json.dumps({"metadata": "x" * 500, "is_error": True, "result": "Not logged in"})
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout=envelope, stderr=""))
    with pytest.raises(LLMError, match="Not logged in"):
        ClaudeCode().complete("rules", "evidence", 1)


def test_codex_does_not_run_without_a_tool_free_transport(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="{}", stderr=""))
    with pytest.raises(LLMError, match="tool-free"):
        Codex().complete("rules", "evidence", 1)
