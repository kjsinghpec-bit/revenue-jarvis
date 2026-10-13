"""Dense (multilingual E5) + sparse (BM25) indexes, persisted inside the SQLite DB."""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache

import numpy as np

from .db import set_meta
from .text import tokenize


@lru_cache(maxsize=2)
def load_encoder(model_name: str, revision: str = "main"):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, revision=revision, device="cpu")


def encode_passages(model, texts: list[str], batch_size: int = 32) -> np.ndarray:
    v = model.encode([f"passage: {t}" for t in texts], batch_size=batch_size, normalize_embeddings=True,
                     show_progress_bar=False, convert_to_numpy=True)
    return v.astype(np.float32)


def encode_query(model, q: str) -> np.ndarray:
    return model.encode([f"query: {q}"], normalize_embeddings=True, convert_to_numpy=True)[0].astype(np.float32)


def build_index(con: sqlite3.Connection, model_name: str, revision: str = "main", progress=None) -> dict:
    rows = con.execute(
        "SELECT c.id, c.text, c.heading, d.short_name FROM chunks c JOIN documents d ON d.id=c.doc_id "
        "WHERE c.id NOT IN (SELECT chunk_id FROM embeddings) ORDER BY c.doc_id, c.ordinal"
    ).fetchall()
    model = load_encoder(model_name, revision)
    B = 64
    for i in range(0, len(rows), B):
        batch = rows[i:i + B]
        texts = [(f"{r['short_name']}: " if r["short_name"] and r["short_name"] != "Bhumbak" else "") + r["text"] for r in batch]
        vecs = encode_passages(model, texts)
        for r, v, t in zip(batch, vecs, texts, strict=False):
            con.execute("INSERT OR REPLACE INTO embeddings VALUES (?,?,?)", (r["id"], int(v.shape[0]), v.tobytes()))
            con.execute("INSERT OR REPLACE INTO bm25_tokens VALUES (?,?)", (r["id"], json.dumps(tokenize(t), ensure_ascii=False)))
        con.commit()
        if progress:
            progress(min(i + B, len(rows)), len(rows))
    set_meta(con, "embed_model", model_name)
    set_meta(con, "embed_revision", revision)
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    return {"new": len(rows), "total_vectors": n}
