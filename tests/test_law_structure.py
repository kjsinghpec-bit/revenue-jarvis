from pathlib import Path

import pytest

from revenue_jarvis.ingest.laws import split_sections

LAWS = Path(__file__).resolve().parents[1] / "data" / "laws"


def test_lowercase_manual_heading_not_merged():
    parts = split_sections((LAWS / "plrm_ch18.txt").read_text())
    assert any(sec == "18.4" and "who may apply" in text for sec, text in parts)
    assert not any(sec == "18.3" and "18.4 who may apply" in text for sec, text in parts)


def test_vcl_contents_not_numbered_as_act_provisions():
    parts = split_sections((LAWS / "vcl_act_1961.txt").read_text())
    assert not any(sec == "20B" for sec, _ in parts)
    assert any(sec == "7" and "collector" in body.casefold() for sec, body in parts)


def test_preamble_preserved():
    parts = split_sections("THE ACT\nPreamble.\n1. Short title.\nBody")
    assert any(sec is None and "Preamble." in body for sec, body in parts)


def test_typed_combined_act_and_rules():
    from revenue_jarvis.ingest.laws import split_provisions
    parts = split_provisions((LAWS / "consolidation_act_1948_rules_1949.txt").read_text(), "act")
    assert any(p.kind == "rule" and p.section == "1" and "These rules may be called" in p.text for p in parts)
    assert any(p.kind == "section" and p.section == "1" and "This Act may be called" in p.text for p in parts)
    assert all(not p.section for p in parts if p.kind == "reference")


def test_manual_appendix_question_not_a_paragraph():
    from revenue_jarvis.ingest.laws import split_provisions
    parts = split_provisions((LAWS / "plrm_ch07.txt").read_text(), "manual")
    assert all(p.section != "10" for p in parts if "Did the field kanungo" in p.text)


@pytest.mark.parametrize("path", sorted(LAWS.glob("*.txt")), ids=lambda p: p.stem)
def test_existing_source_files_preserve_text_in_structured_parts(path):
    import json
    from revenue_jarvis.ingest.laws import split_provisions
    kinds = {m["slug"]: m["kind"] for m in json.loads((LAWS / "manifest.json").read_text())}
    parts = split_provisions(path.read_text(), kinds[path.stem])
    assert parts and all(p.text.strip() for p in parts)
    # Each provision group has a heading; its later windows may be continuations.
    for number in {p.section for p in parts if p.section}:
        assert any(p.section == number and any(ch.isdigit() for ch in p.text[:120]) for p in parts)
