"""Identify the code and corpus loaded by a running Jarvis process."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3


def source_revision(root: Path | None = None) -> str:
    root = root or Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*.py')):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()


def corpus_revision(con: sqlite3.Connection) -> str:
    """Exclude history/profiles so ordinary questions don't force a restart."""
    digest = hashlib.sha256()
    queries = [
        'SELECT * FROM documents ORDER BY id',
        'SELECT * FROM chunks ORDER BY id',
        'SELECT * FROM embeddings ORDER BY chunk_id',
        'SELECT * FROM bm25_tokens ORDER BY chunk_id',
        'SELECT doc_id,pdf_page,printed_label,text_clean,quality,is_front_matter,image_sha256 FROM pages ORDER BY doc_id,pdf_page',
        "SELECT key,value FROM meta WHERE key IN ('embed_model','embed_revision') ORDER BY key",
    ]
    for query in queries:
        digest.update(query.encode())
        for row in con.execute(query):
            for value in row:
                data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
                digest.update(str(len(data)).encode() + b':' + data)
    return digest.hexdigest()
