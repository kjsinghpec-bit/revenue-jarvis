"""Release criteria require live results and a human audit bound to each answer."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import fields

from .answer import validate
from .grounding import check_generated, numeric_facts
from .retrieve import Evidence


def answer_hash(answer: dict) -> str:
    return hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def assess_release(records: list[dict]) -> list[dict]:
    live = [r for r in records if r.get("mode") == "live" and r.get("answer", {}).get("backend") in {"claude-code", "codex"}]
    names = ("grounding", "citation", "language", "latency", "coverage")
    gates = {name: {"name": name, "status": "blocked", "reason": "Missing live results or bound human audit."} for name in names}
    audited = []
    safe = []
    ev_fields = {f.name for f in fields(Evidence)}
    for record in live:
        answer = record["answer"]
        audit = record.get("audit", {})
        if audit.get("reviewer") and audit.get("answer_sha256") == answer_hash(answer) and audit.get("answer_id") == answer.get("answer_id"):
            audited.append(record)
        try:
            if answer.get("status") != "answered":
                continue
            evs = [Evidence(**{k: v for k, v in e.items() if k in ev_fields}) for e in answer.get("evidence", [])]
            validated, _ = validate(answer, evs)
            if not (validated.claims or validated.law_support) or validated.status != "answered":
                continue
            check_generated(answer.get("spoken", ""))
            supported = set().union(*(numeric_facts(s.quote) for c in validated.claims + validated.law_support for s in c.support))
            if numeric_facts(answer.get("spoken", "")) - supported:
                continue
            safe.append(record)
        except (ValueError, TypeError, KeyError):
            continue
    audited_questions = {r.get("question_id") for r in audited if r.get("question_id")}
    if len(audited_questions) >= 20:
        okay = all(r.get("audit", {}).get("numeric_correct") is True and r.get("audit", {}).get("supports_claims") is True for r in audited)
        gates["grounding"].update(status="pass" if okay and all(r in safe for r in audited if r["answer"].get("status") == "answered") else "fail",
                                  reason=f"{len(audited_questions)} distinct questions audited for numbers and full claim support.")
        okay = all(r["audit"].get("citation_correct") is True and r["audit"].get("clicked_citations") is True for r in audited)
        gates["citation"].update(status="pass" if okay else "fail", reason="Audit must check every locator and click citations across multiple answers.")
    hindi = [r for r in live if r["answer"].get("input_language") == "hi"]
    if len({r.get("question_id") for r in hindi if r.get("question_id")}) >= 10:
        okay = True
        for r in hindi:
            a = r["answer"]
            generated = [a.get("spoken", ""), *a.get("missing_facts", []), *a.get("caveats", [])]
            generated += [c["text"] for label in ("claims", "law_support", "conflicts") for c in a.get(label, [])]
            try:
                for text in generated: check_generated(text)
                okay &= a.get("language") in {"en", "pa"} and a.get("status") in {"answered", "insufficient", "need_facts"}
            except ValueError:
                okay = False
        gates["language"].update(status="pass" if okay else "fail", reason="10+ distinct Hindi inputs must synthesize in English/Gurmukhi without prohibited script.")
    latencies = [r["elapsed_ms"] for r in safe if isinstance(r.get("elapsed_ms"), (float, int)) and math.isfinite(r["elapsed_ms"]) and r["elapsed_ms"] > 0]
    if len(latencies) >= 50:
        median = statistics.median(latencies)
        p95 = sorted(latencies)[math.ceil(len(latencies) * 0.95) - 1]
        gates["latency"].update(status="pass" if median <= 15000 and p95 <= 25000 else "fail", reason=f"Validated live HTTP round trips: median {median:.1f} ms, p95 {p95:.1f} ms; target 15000/25000 ms.")
    if len(audited_questions) >= 30:
        usable = {r.get("question_id") for r in safe if r in audited and r["audit"].get("supports_claims") is True and r["audit"].get("numeric_correct") is True and r["audit"].get("citation_correct") is True}
        ratio = len(usable) / len(audited_questions)
        gates["coverage"].update(status="pass" if ratio >= 0.9 else "fail", reason=f"{len(usable)}/{len(audited_questions)} audited distinct questions have supported substantive answers.")
    return list(gates.values())
