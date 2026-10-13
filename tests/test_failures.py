"""Failure-mode tests: missing CLI, timeout, broken output, stale index, missing OCR, unreadable pages."""
import json
import os
import stat
import sys
from pathlib import Path

import pytest

from revenue_jarvis import db as dbm
from revenue_jarvis.answer import Jarvis
from revenue_jarvis.ingest.book import ingest_book
from revenue_jarvis.llm import ClaudeCode, Codex, LLMError, pick_backend
from revenue_jarvis.retrieve import Retriever


def _fake_cli(tmp_path: Path, name: str, body: str) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    exe = bindir / name
    exe.write_text(f"#!{sys.executable}\n{body}\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return bindir


def test_missing_cli_means_sources_only(kb, monkeypatch, tmp_path):
    s, con = kb
    monkeypatch.setenv("PATH", str(tmp_path))          # nothing on PATH
    s.llm_backend = "auto"
    assert pick_backend("auto") is None
    a = Jarvis(s, con, backend="auto").ask("partition application")
    assert a.status == "sources_only" and any("No thinking engine" in w for w in a.warnings)


def test_claude_cli_end_to_end_and_no_api_key_leak(kb, monkeypatch, tmp_path):
    s, con = kb
    quote = con.execute("SELECT text FROM chunks WHERE id='b167'").fetchone()[0]
    reply = {"status": "answered", "spoken": "Sir, any co-sharer may apply.",
             "claims": [{"text": "Any co-sharer may apply.", "source_ids": ["B1"], "support": [{"source_id": "B1", "quote": quote}]}]}
    body = ("import sys, json, os\n"
            "args = sys.argv[1:]\n"
            "assert '-p' in args and '--disallowedTools' in args and '--max-turns' in args\n"
            "assert 'ANTHROPIC_API_KEY' not in os.environ, 'API key must never reach the CLI'\n"
            "prompt = sys.stdin.read()\n"
            "out = " + repr(json.dumps(reply)) + " if 'EVIDENCE' in prompt else '[\"ਤਕਸੀਮ\"]'\n"
            "print(json.dumps({'type': 'result', 'is_error': False, 'result': out}))")
    monkeypatch.setenv("PATH", str(_fake_cli(tmp_path, "claude", body)) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-be-used")
    s.llm_query_rewrite = True
    s.llm_backend = "auto"
    a = Jarvis(s, con, backend="auto").ask("Who may apply for partition?")
    assert a.backend == "claude-code" and a.status == "answered" and a.claims


def test_claude_cli_timeout(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(_fake_cli(tmp_path, "claude", "import time; time.sleep(5)")) + os.pathsep + os.environ["PATH"])
    with pytest.raises(LLMError, match="timed out"):
        ClaudeCode().complete("sys", "prompt", timeout=1)


def test_claude_cli_error_reported(monkeypatch, tmp_path):
    body = "import sys; print('not logged in', file=sys.stderr); sys.exit(1)"
    monkeypatch.setenv("PATH", str(_fake_cli(tmp_path, "claude", body)) + os.pathsep + os.environ["PATH"])
    with pytest.raises(LLMError, match="not logged in"):
        ClaudeCode().complete("sys", "prompt", timeout=5)


def test_codex_fallback_withholds_synthesis_without_tool_isolation(monkeypatch, tmp_path):
    body = ("import sys\nargs = sys.argv[1:]\nout = args[args.index('--output-last-message') + 1]\n"
            "sys.stdin.read()\nopen(out, 'w').write('{\"status\": \"insufficient\", \"spoken\": \"Sir\"}')")
    monkeypatch.setenv("PATH", str(_fake_cli(tmp_path, "codex", body)))
    b = pick_backend("auto")
    assert isinstance(b, Codex)
    with pytest.raises(LLMError, match="tool-free"):
        b.complete("sys", "p", timeout=5)


def test_stale_index_detected(kb):
    s, con = kb
    con.execute("INSERT INTO chunks(id,doc_id,ordinal,source_type,text,pdf_page_start) VALUES ('new',1,1,'book','ਨਵਾਂ ਪੰਨਾ',200)")
    con.commit()
    h = dbm.health(con)
    assert h["chunks_without_vector"] == 1 and h["integrity"] == "ok"
    assert "new" not in Retriever(con, "x").pools["book"].ids      # never served without a vector


def test_missing_ocr_folder_gives_empty_book(tmp_path):
    con = dbm.connect(tmp_path / "x.db")
    stats = ingest_book(con, tmp_path / "does-not-exist")
    assert stats["pages"] == 0 and stats["chunks"] == 0


def test_unreadable_page_is_flagged_not_indexed(tmp_path):
    ocr = tmp_path / "ocr"
    ocr.mkdir()
    good = {"pdf_page": 120, "text_raw": "105\nਮੁਸੰਨਾ ਤਿਆਰ ਕਰਨ ਦੀ ਵਿਧੀ ਬਾਰੇ ਹਦਾਇਤਾਂ ਇਸ ਪੰਨੇ ਤੇ ਹਨ।",
            "lines": [{"text": "105"}, {"text": "ਮੁਸੰਨਾ ਤਿਆਰ ਕਰਨ ਦੀ ਵਿਧੀ"}], "n_lines": 2, "failed_lines": 0}
    blank = {"pdf_page": 30, "text_raw": "", "lines": [], "n_lines": 0, "failed_lines": 3}
    for rec in (good, blank):
        (ocr / f"page_{rec['pdf_page']:04d}.json").write_text(json.dumps(rec, ensure_ascii=False))
    con = dbm.connect(tmp_path / "x.db")
    st = ingest_book(con, ocr)
    assert st["empty_pages"] == 1 and st["labels_verified"] == 1
    assert con.execute("SELECT quality FROM pages WHERE pdf_page=30").fetchone()[0] == "empty"
    assert con.execute("SELECT COUNT(*) FROM chunks WHERE pdf_page_start=30").fetchone()[0] == 0
