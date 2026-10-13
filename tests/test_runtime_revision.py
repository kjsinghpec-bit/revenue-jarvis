from fastapi.testclient import TestClient
from revenue_jarvis import server


def test_server_reports_restart_needed_after_source_changes(kb,tmp_path,monkeypatch):
    from revenue_jarvis.runtime import source_revision
    folder=tmp_path/'source';folder.mkdir();file=folder/'answer.py';file.write_text('old code')
    monkeypatch.setattr(server,'source_revision',lambda:source_revision(folder))
    settings,con=kb;con.close()
    client=TestClient(server.create_app(settings))
    initial=client.get('/api/status').json()
    assert initial['restart_required'] is False
    file.write_text('updated code')
    changed=client.get('/api/status').json()
    assert changed['restart_required'] is True
    assert changed['runtime_revision']==initial['runtime_revision']
    assert client.post('/api/ask',json={'question':'partition'}).status_code==503
    assert client.get('/api/history').json()==[]


def test_history_writes_do_not_invalidate_corpus_but_index_change_does(kb):
    from revenue_jarvis.runtime import corpus_revision
    _,con=kb
    before=corpus_revision(con)
    con.execute("INSERT INTO qa_log(question,status) VALUES ('partition','sources_only')")
    assert corpus_revision(con)==before
    con.execute("UPDATE chunks SET text=text || ' corrected' WHERE id='b167'")
    assert corpus_revision(con)!=before


def test_database_change_requires_restart_before_next_answer(kb):
    settings,con=kb
    client=TestClient(server.create_app(settings))
    assert client.get('/api/status').json()['restart_required'] is False
    con.execute("UPDATE chunks SET text=text || ' corrected' WHERE id='b167'");con.commit()
    assert client.get('/api/status').json()['restart_required'] is True
    assert client.post('/api/ask',json={'question':'partition'}).status_code==503
    con.close()
