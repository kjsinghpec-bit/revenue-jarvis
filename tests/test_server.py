from fastapi.testclient import TestClient

from revenue_jarvis import server


def test_api_status_ask_history(kb, monkeypatch):
    s, con = kb
    con.close()
    client = TestClient(server.create_app(s))
    st = client.get("/api/status").json()
    assert st["book_pages"] == 4 and st["backend"] == "sources-only" and len(st["laws"]) == 2
    r = client.post("/api/ask", json={"question": "Who may apply for partition?"})
    assert r.status_code == 200 and r.json()["status"] == "sources_only"
    assert client.get("/api/history").json()[0]["question"] == "Who may apply for partition?"
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_validation_and_missing_pdf(kb):
    s, con = kb
    con.close()
    client = TestClient(server.create_app(s))
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.get("/api/page/119.png").status_code == 404
    assert client.get("/api/page/119/text").json()["printed_label"] == "104"


def test_request_profile_includes_queue_and_initialization(kb):
    import json
    s, con = kb
    con.close()
    client = TestClient(server.create_app(s))
    a = client.post("/api/ask", json={"question": "partition"}).json()
    assert "queue_wait" in a["timings"] and "initialize" in a["timings"]
    records = [json.loads(line) for line in (s.data_dir / "timings.jsonl").read_text().splitlines()]
    assert any(r["event"] == "request" and r["answer_id"] == a["answer_id"] and r["timings"]["request_total"] >= r["timings"]["llm"] for r in records)
