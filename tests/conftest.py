"""Shared fixtures: a tiny knowledge base with deterministic fake vectors (no model download needed)."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest

from revenue_jarvis import db as dbm
from revenue_jarvis import retrieve
from revenue_jarvis.config import Settings
from revenue_jarvis.text import tokenize

DIM = 384


def fake_vec(text: str) -> np.ndarray:
    """Bag-of-tokens hashed into 384 dims: similar texts -> similar vectors. Deterministic."""
    v = np.zeros(DIM, np.float32)
    for t in tokenize(text):
        v[int(hashlib.md5(t.encode()).hexdigest(), 16) % DIM] += 1
    n = np.linalg.norm(v)
    return v / n if n else v


BOOK = {
    119: "ਮੁਸੰਨਾ ਤਿਆਰ ਕਰਨ ਲਈ ਨਿਮਨ ਲਿਖਤ ਵਿਧੀ ਅਪਣਾਈ ਜਾਵੇ। ਗੁੰਮ ਹੋਏ ਇੰਤਕਾਲ ਦੀ ਭਾਲ ਕਰਨ ਲਈ ਹਰ ਮੁਮਕਿਨ ਕੋਸ਼ਿਸ਼ ਕੀਤੀ ਜਾਵੇ। ਕਲੈਕਟਰ ਦੀ ਪ੍ਰਵਾਨਗੀ",
    167: "ਤਕਸੀਮ ਲਈ ਦਰਖ਼ਾਸਤ ਕੋਈ ਵੀ ਹਿੱਸੇਦਾਰ ਮਾਲ ਅਧਿਕਾਰੀ ਕੋਲ ਦੇ ਸਕਦਾ ਹੈ। ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ",
    246: "ਸ਼ਾਮਲਾਤ ਦੇਹ ਵਿੱਚੋਂ ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾਕਾਰ ਦੀ ਬੇਦਖ਼ਲੀ ਪੰਚਾਇਤ ਦੀ ਦਰਖ਼ਾਸਤ ਤੇ ਕੁਲੈਕਟਰ ਕਰੇਗਾ।",
    10: "ਇੰਡੈਕਸ ਚੈਪਟਰ ਤਕਸੀਮ ਇੰਤਕਾਲ ਸ਼ਾਮਲਾਤ ਮੁਸੰਨਾ",   # contents page: must be excluded
}
LAWS = [("plra_1887", "PLRA 1887", "111", "111. Application for partition. Any joint owner of land may apply to a Revenue Officer for partition of his share."),
        ("vcl_1961", "VCLA 1961", "7", "7. Power to put panchayat in possession. Collector may eject unauthorised occupant of shamlat deh.")]


@pytest.fixture()
def kb(tmp_path, monkeypatch):
    path = tmp_path / "jarvis.db"
    con = dbm.connect(path)
    book_id = con.execute("INSERT INTO documents(kind,slug,title,short_name) VALUES ('book','bhumbak','Zameen Di Guide','Bhumbak')").lastrowid
    for p, txt in BOOK.items():
        front = int(p < 16)
        con.execute("INSERT INTO pages(doc_id,pdf_page,printed_label,text_raw,text_clean,quality,is_front_matter) VALUES (?,?,?,?,?,?,?)",
                    (book_id, p, None if front else str(p - 15), txt, txt, "ok", front))
        cid = f"b{p}"
        con.execute("INSERT INTO chunks(id,doc_id,ordinal,source_type,text,pdf_page_start,pdf_page_end,printed_labels,excluded) VALUES (?,?,?,?,?,?,?,?,?)",
                    (cid, book_id, p * 100, "book", txt, p, p, None if front else str(p - 15), front))
    for slug, short, sec, txt in LAWS:
        did = con.execute("INSERT INTO documents(kind,slug,title,short_name,jurisdiction) VALUES ('law',?,?,?,'Punjab')", (slug, short, short)).lastrowid
        con.execute("INSERT INTO chunks(id,doc_id,ordinal,source_type,text,section,quality_flags) VALUES (?,?,?,?,?,?,?)", (f"l{slug}", did, 0, "law", txt, sec, "structure_v2,provision_kind=section"))
    for r in con.execute("SELECT id, text FROM chunks").fetchall():
        con.execute("INSERT INTO embeddings VALUES (?,?,?)", (r["id"], DIM, fake_vec(r["text"]).tobytes()))
        con.execute("INSERT INTO bm25_tokens VALUES (?,?)", (r["id"], json.dumps(tokenize(r["text"]), ensure_ascii=False)))
    con.commit()
    monkeypatch.setattr(retrieve, "load_encoder", lambda *a, **k: None)
    monkeypatch.setattr(retrieve, "encode_query", lambda model, q: fake_vec(q))
    settings = Settings(data_dir=tmp_path, llm_backend="none", llm_query_rewrite=False)
    return settings, con
