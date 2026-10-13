def test_release_gate_does_not_pass_without_live_audited_results():
    from revenue_jarvis.release import assess_release
    gates = assess_release([])
    assert len(gates) == 5 and all(g["status"] == "blocked" for g in gates)


def test_fast_sources_only_responses_cannot_pass_coverage_or_latency():
    from revenue_jarvis.release import assess_release
    records = [{"mode": "live", "elapsed_ms": 1, "answer": {"backend": "claude-code", "status": "sources_only", "claims": [], "law_support": []}} for _ in range(50)]
    gates = {g["name"]: g for g in assess_release(records)}
    assert gates["coverage"]["status"] != "pass" and gates["latency"]["status"] != "pass"


def test_mocked_runs_cannot_certify_production():
    from revenue_jarvis.release import assess_release
    records = [{"mode": "test", "elapsed_ms": 1, "answer": {"backend": "fake", "status": "answered", "claims": [{"text": "The fee is ₹100.", "source_ids": ["B1"]}]}} for _ in range(50)]
    assert all(g["status"] != "pass" for g in assess_release(records))


def reviewed_records():
    import hashlib
    import json
    from dataclasses import asdict
    from revenue_jarvis.retrieve import Evidence
    records = []
    for i in range(50):
        source = asdict(Evidence("B1", "fee", "book", "The fee is ₹100.", "Fixture", "Fixture", pdf_page=23))
        answer = {"answer_id": str(i), "backend": "claude-code", "status": "answered", "language": "en", "input_language": "hi" if i < 10 else "en",
                  "spoken": "Sir, the fee is ₹100.", "claims": [{"text": "The fee is ₹100.", "source_ids": ["B1"], "support": [{"source_id": "B1", "quote": "The fee is ₹100."}]}], "evidence": [source]}
        digest = hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        records.append({"mode": "live", "question_id": f"q{i}", "elapsed_ms": 1000,
                        "answer": answer, "audit": {"reviewer": "test fixture", "answer_id": str(i), "answer_sha256": digest,
                        "numeric_correct": True, "supports_claims": True, "citation_correct": True, "clicked_citations": True}})
    return records


def test_complete_reviewed_measurements_can_pass_all_gates():
    from revenue_jarvis.release import assess_release
    assert all(g["status"] == "pass" for g in assess_release(reviewed_records()))


def test_changed_answers_invalidate_old_audits():
    from revenue_jarvis.release import assess_release
    records = reviewed_records()
    for r in records:
        r["answer"]["claims"][0]["text"] = "The fee is ₹500."
    gates = {g["name"]: g for g in assess_release(records)}
    assert gates["grounding"]["status"] == "blocked" and gates["citation"]["status"] == "blocked"
