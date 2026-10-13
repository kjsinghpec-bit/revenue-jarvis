"""One SQLite database holds everything: sources, OCR pages, chunks, vectors, the Q&A log."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('book','law')),
  slug TEXT UNIQUE NOT NULL, title TEXT, short_name TEXT, jurisdiction TEXT, doc_type TEXT,
  source_url TEXT, sha256 TEXT, retrieved TEXT, complete INTEGER DEFAULT 1, notes TEXT);
CREATE TABLE IF NOT EXISTS pages(
  doc_id INTEGER NOT NULL REFERENCES documents(id), pdf_page INTEGER NOT NULL,
  printed_label TEXT, label_source TEXT, text_raw TEXT, text_clean TEXT,
  n_lines INTEGER, failed_lines INTEGER, recovered_lines INTEGER,
  quality TEXT, is_front_matter INTEGER DEFAULT 0, ocr_engine TEXT, image_sha256 TEXT,
  PRIMARY KEY(doc_id, pdf_page));
CREATE TABLE IF NOT EXISTS chunks(
  id TEXT PRIMARY KEY, doc_id INTEGER NOT NULL REFERENCES documents(id), ordinal INTEGER,
  source_type TEXT NOT NULL CHECK(source_type IN ('book','law')),
  text TEXT NOT NULL, pdf_page_start INTEGER, pdf_page_end INTEGER, printed_labels TEXT,
  section TEXT, heading TEXT, quality_flags TEXT, excluded INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON chunks(doc_id, ordinal);
CREATE TABLE IF NOT EXISTS embeddings(chunk_id TEXT PRIMARY KEY REFERENCES chunks(id), dim INTEGER, vec BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS bm25_tokens(chunk_id TEXT PRIMARY KEY REFERENCES chunks(id), tokens TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS qa_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT DEFAULT (datetime('now')), question TEXT, language TEXT,
  backend TEXT, status TEXT, answer_json TEXT, evidence_ids TEXT, latency_ms INTEGER);
CREATE TABLE IF NOT EXISTS eval_results(
  run_id TEXT, question_id TEXT, language TEXT, question TEXT, gold_pages TEXT, retrieved_pages TEXT,
  hit_at_5 INTEGER, latency_ms INTEGER, error_bucket TEXT, ts TEXT DEFAULT (datetime('now')));
"""


def connect(path: Path | str, *, readonly: bool = False) -> sqlite3.Connection:
    path = Path(path)
    if readonly:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False, timeout=10)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(path), check_same_thread=False, timeout=10)
        con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=10000")
    if not readonly:
        con.executescript(DDL)
        from .ocr_review import REVIEW_DDL
        con.execute(REVIEW_DDL)
        con.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        con.commit()
    return con


def get_meta(con: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute("INSERT INTO meta(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def health(con: sqlite3.Connection) -> dict:
    """Integrity and staleness report used by `jarvis doctor` and the tests."""
    q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
    return {
        "integrity": q("PRAGMA integrity_check"),
        "chunks": q("SELECT COUNT(*) FROM chunks"),
        "chunks_without_vector": q("SELECT COUNT(*) FROM chunks WHERE id NOT IN (SELECT chunk_id FROM embeddings)"),
        "orphan_vectors": q("SELECT COUNT(*) FROM embeddings WHERE chunk_id NOT IN (SELECT id FROM chunks)"),
        "book_pages": q("SELECT COUNT(*) FROM pages"),
        "empty_pages": q("SELECT COUNT(*) FROM pages WHERE quality='empty'"),
        "pages_without_label": q("SELECT COUNT(*) FROM pages WHERE printed_label IS NULL AND is_front_matter=0"),
        "laws": q("SELECT COUNT(*) FROM documents WHERE kind='law'"),
    }
