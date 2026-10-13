"""Scan review provenance and read-only checks for a staged OCR index.

Extraction quality is never a claim of transcription or legal accuracy.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

import numpy as np

from .text import tokenize

REVIEW_DDL = """CREATE TABLE IF NOT EXISTS page_reviews(
  doc_id INTEGER NOT NULL REFERENCES documents(id), pdf_page INTEGER NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('needs_review','scan_verified')),
  text_sha256 TEXT NOT NULL, image_sha256 TEXT NOT NULL,
  reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY(doc_id,pdf_page),
  FOREIGN KEY(doc_id,pdf_page) REFERENCES pages(doc_id,pdf_page) ON DELETE CASCADE);"""


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def page_review(con: sqlite3.Connection, doc_id: int, page: int, excerpt: str | None = None) -> dict:
    row = con.execute('SELECT text_clean,image_sha256,quality FROM pages WHERE doc_id=? AND pdf_page=?', (doc_id, page)).fetchone()
    result = {'ocr_status': 'needs_review', 'scan_verified': False}
    if not row:
        return result
    text, image, quality = row
    if excerpt is not None and ' '.join(excerpt.split()) not in ' '.join((text or '').split()):
        return result  # a stale retrieved chunk cannot inherit a corrected page's review
    result['ocr_status'] = 'extracted' if quality == 'ok' else 'needs_review'
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='page_reviews'").fetchone():
        return result  # legacy/read-only databases stay unverified
    review = con.execute('SELECT status,text_sha256,image_sha256 FROM page_reviews WHERE doc_id=? AND pdf_page=?', (doc_id, page)).fetchone()
    if review:
        status, reviewed_text, reviewed_image = review
        matches = bool(image) and reviewed_text == text_hash(text or '') and reviewed_image == image
        result['ocr_status'] = status if matches else 'needs_review'
        result['scan_verified'] = matches and status == 'scan_verified'
    return result


def record_review(con: sqlite3.Connection, doc_id: int, page: int, status: str,
                  reviewer: str, text_sha256: str, image_sha256: str) -> None:
    """Record an explicit scan comparison; caller supplies the exact reviewed hashes."""
    if status not in ('needs_review', 'scan_verified') or not reviewer.strip():
        raise ValueError('Review needs an explicit status and reviewer')
    row = con.execute('SELECT text_clean,image_sha256 FROM pages WHERE doc_id=? AND pdf_page=?', (doc_id, page)).fetchone()
    if not row or not image_sha256 or row[1] != image_sha256 or text_hash(row[0] or '') != text_sha256:
        raise ValueError('Review hashes do not match the current page text and scan')
    con.execute(REVIEW_DDL)
    con.execute("INSERT INTO page_reviews(doc_id,pdf_page,status,text_sha256,image_sha256,reviewer) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(doc_id,pdf_page) DO UPDATE SET status=excluded.status,text_sha256=excluded.text_sha256,"
                "image_sha256=excluded.image_sha256,reviewer=excluded.reviewer,reviewed_at=datetime('now')",
                (doc_id, page, status, text_sha256, image_sha256, reviewer.strip()))
    con.commit()


def check_import(con: sqlite3.Connection, expected_pages: list[dict] | None = None,
                 baseline: sqlite3.Connection | None = None) -> dict:
    """Structural import gate, not an OCR accuracy or retrieval certification."""
    errors = []
    if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        errors.append('SQLite integrity check failed')
    if con.execute('PRAGMA foreign_key_check').fetchall():
        errors.append('Foreign key violations')
    for table in ('embeddings', 'bm25_tokens'):
        count = con.execute(f'SELECT count(*) FROM {table} WHERE chunk_id NOT IN (SELECT id FROM chunks)').fetchone()[0]
        if count:
            errors.append(f'{count} orphan records in {table}')
    pages = {(r['doc_id'], r['pdf_page']): dict(r) for r in con.execute('SELECT * FROM pages')}
    book_pages = set()
    dims = set()
    old = {}
    if baseline:
        old = {r['id']: dict(r) for r in baseline.execute('SELECT c.id,c.text,e.vec FROM chunks c LEFT JOIN embeddings e ON c.id=e.chunk_id')}
        for r in baseline.execute("SELECT p.doc_id,p.pdf_page FROM pages p JOIN documents d ON p.doc_id=d.id WHERE d.kind='book'"):
            if (r['doc_id'], r['pdf_page']) not in pages:
                errors.append(f"Missing baseline book page: document {r['doc_id']}, PDF page {r['pdf_page']}")
        law_docs = "SELECT * FROM documents WHERE kind='law'"
        law_chunks = ("SELECT c.*,e.dim,e.vec,t.tokens FROM chunks c JOIN documents d ON c.doc_id=d.id "
                      "LEFT JOIN embeddings e ON e.chunk_id=c.id LEFT JOIN bm25_tokens t ON t.chunk_id=c.id WHERE d.kind='law'")
        for query in (law_docs, law_chunks):
            previous = {r['id']: dict(r) for r in baseline.execute(query)}
            current = {r['id']: dict(r) for r in con.execute(query)}
            if previous != current:
                errors.append('Existing law corpus changed during OCR import (documents/chunks/index)')
                break
    rows = con.execute('SELECT c.*,d.short_name,e.dim,e.vec,t.tokens FROM chunks c JOIN documents d ON d.id=c.doc_id '
                       'LEFT JOIN embeddings e ON e.chunk_id=c.id LEFT JOIN bm25_tokens t ON t.chunk_id=c.id WHERE c.excluded=0').fetchall()
    for r in rows:
        cid = r['id']
        if r['vec'] is None:
            errors.append(f'{cid}: missing vector')
        elif not r['dim'] or len(r['vec']) != r['dim'] * 4:
            errors.append(f'{cid}: invalid vector dimensions')
        else:
            dims.add(r['dim'])
            vector = np.frombuffer(r['vec'], dtype=np.float32)
            if not np.isfinite(vector).all() or np.linalg.norm(vector) == 0:
                errors.append(f'{cid}: invalid vector values')
        passage = (f"{r['short_name']}: " if r['short_name'] and r['short_name'] != 'Bhumbak' else '') + r['text']
        try:
            tokens = json.loads(r['tokens']) if r['tokens'] else None
        except (ValueError, TypeError):
            tokens = None
        if tokens != tokenize(passage):
            errors.append(f'{cid}: missing or stale BM25 tokens')
        if cid in old and old[cid]['text'] != r['text'] and old[cid]['vec'] == r['vec']:
            errors.append(f'{cid}: changed text reuses baseline vector')
        if r['source_type'] == 'book':
            key = (r['doc_id'], r['pdf_page_start'])
            book_pages.add(key)
            page = pages.get(key)
            if not page or r['pdf_page_start'] != r['pdf_page_end']:
                errors.append(f'{cid}: invalid book page mapping')
            elif ' '.join(r['text'].split()) not in ' '.join((page['text_clean'] or '').split()):
                errors.append(f'{cid}: chunk does not match page text')
            if page and r['printed_labels'] != page['printed_label']:
                errors.append(f'{cid}: printed page label mismatch')
    if len(dims) > 1:
        errors.append('Inconsistent vector dimensions across searchable chunks')
    if baseline:
        previous_searchable = {(r['doc_id'],r['pdf_page_start']) for r in baseline.execute("SELECT doc_id,pdf_page_start FROM chunks WHERE source_type='book' AND excluded=0")}
        for key in sorted(previous_searchable - book_pages):
            errors.append(f'Missing searchable baseline book page: document {key[0]}, PDF page {key[1]}')
    for expected in expected_pages or []:
        key = (expected['doc_id'], expected['pdf_page'])
        page = pages.get(key)
        if not page or text_hash(page['text_clean'] or '') != expected['text_sha256']:
            errors.append(f'{key}: corrected page text hash mismatch')
        elif key not in book_pages and len((page['text_clean'] or '').strip()) >= 40:
            errors.append(f'{key}: corrected page has no searchable chunks')
        if page and 'printed_page' in expected and page['printed_label'] != expected['printed_page']:
            errors.append(f'{key}: expected printed page label mismatch')
    verified = sum(page_review(con, *key)['scan_verified'] for key in book_pages)
    return {'passed': not errors, 'errors': errors, 'searchable_chunks': len(rows),
            'scan_verified_book_pages': verified, 'unverified_book_pages': len(book_pages) - verified,
            'scope': 'Index consistency only; OCR accuracy and retrieval regression checks are separate.'}
