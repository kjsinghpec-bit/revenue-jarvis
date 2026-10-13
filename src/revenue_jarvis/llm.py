"""Thinking engines that run on subscriptions you already have (no API keys, no per-token bills).

- ClaudeCode: the `claude` CLI in print mode, logged in with your Claude Pro/Max plan.
- Codex: detected for diagnostics, but synthesis is withheld until a tool-free
  transport exists. A read-only filesystem sandbox is not tool isolation.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Protocol


class LLMError(RuntimeError):
    pass


class Backend(Protocol):
    name: str

    def complete(self, system: str, prompt: str, timeout: int) -> str: ...


@dataclass
class ClaudeCode:
    model: str | None = None
    name: str = "claude-code"

    @staticmethod
    def available() -> bool:
        return shutil.which("claude") is not None

    def complete(self, system: str, prompt: str, timeout: int) -> str:
        cmd = ["claude", "-p", "--output-format", "json", "--max-turns", "1",
               "--system-prompt", system, "--safe-mode", "--tools", "",
               "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
               "--disable-slash-commands", "--disallowedTools", "mcp__*"]
        if self.model:
            cmd += ["--model", self.model]
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}   # force subscription login, never API billing
        try:
            out = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, env=env,
                                 cwd=tempfile.gettempdir(), check=False)
        except subprocess.TimeoutExpired as e:
            raise LLMError(f"Claude Code timed out after {timeout}s") from e
        except OSError as e:
            raise LLMError(f"Claude Code unavailable: {type(e).__name__}") from e
        try:
            data = json.loads(out.stdout)
        except json.JSONDecodeError:
            if out.returncode != 0:
                raise LLMError(f"Claude Code failed: {(out.stderr or out.stdout).strip()[:300]}")
            return out.stdout.strip()
        if not isinstance(data, dict):
            raise LLMError("Claude Code returned an invalid result envelope")
        if data.get("is_error"):
            raise LLMError(f"Claude Code error: {str(data.get('result'))[:300]}")
        if out.returncode != 0:
            raise LLMError(f"Claude Code failed: {str(data.get('result') or out.stderr or 'nonzero exit')[:300]}")
        return str(data.get("result", "")).strip()


@dataclass
class Codex:
    name: str = "codex"

    @staticmethod
    def available() -> bool:
        return shutil.which("codex") is not None

    def complete(self, system: str, prompt: str, timeout: int) -> str:
        raise LLMError("Codex CLI has no verified tool-free transport; synthesis is withheld. Use Claude or sources-only.")


def pick_backend(preference: str = "auto", claude_model: str | None = None) -> Backend | None:
    if preference in ("auto", "claude") and ClaudeCode.available():
        return ClaudeCode(model=claude_model)
    if preference in ("auto", "codex") and Codex.available():
        return Codex()
    return None
