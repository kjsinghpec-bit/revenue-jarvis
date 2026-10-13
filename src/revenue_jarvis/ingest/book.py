"""Load per-page OCR JSON into SQLite: pages, printed page labels, and page-linked chunks."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path

from ..text import ascii_digits, clean_ocr

BOOK_SLUG = "bhumbak-zameen-di-guide"
BOOK_TITLE = "Jivtesh Zameen Di Guide (ਜਿਵਤੇਸ਼ ਜ਼ਮੀਨ ਦੀ ਗਾਈਡ) - Sohan Lal Bhumbak, PCS (Retd.), Krishna Publishing House, 2022"
BODY_OFFSET = 15          # observed: printed page = PDF page - 15 (verified per page, never assumed)
FIRST_BODY_PDF_PAGE = 16  # PDF pages before this are cover, foreword and contents
CHUNK_CHARS = 700
CHUNK_OVERLAP = 140


def detect_printed_label(lines: list[str], pdf_page: int) -> tuple[str | None, str]:
    """Look for the printed page number in the first/last lines. Accept it only when it agrees with
    the observed body offset; otherwise leave it unknown (never infer an unverified label)."""
    expected = pdf_page - BODY_OFFSET
    cands = lines[:3] + lines[-2:]
    nums = [int(n) for ln in cands for n in re.findall(r"(?<!\d)(\d{1,3})(?!\d)", ascii_digits(ln))]
    if expected >= 1 and expected in nums:
        return str(expected), "ocr_verified"
    return None, "unknown"


def _chunks(text: str) -> list[str]:
    """Paragraph-aware windows of ~CHUNK_CHARS with overlap; numbered clauses stay together where possible."""
    lines = text.splitlines()
    out, cur = [], ""
    for ln in lines:
        if len(cur) + len(ln) + 1 > CHUNK_CHARS and cur:
            out.append(cur.strip())
            cur = cur[-CHUNK_OVERLAP:]
            cut = cur.find("\n")
            cur = cur[cut + 1:] if cut != -1 else cur
        cur += ln + "\n"
    if cur.strip() and (not out or cur.strip() not in out[-1]):
        out.append(cur.strip())
    return out


def ingest_book(con: sqlite3.Connection, ocr_dir: Path, pdf_sha256: str | None = None) -> dict:
    row = con.execute("SELECT id FROM documents WHERE slug=?", (BOOK_SLUG,)).fetchone()
    if row:
        doc_id = row[0]
        con.execute("DELETE FROM embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE doc_id=?)", (doc_id,))
        con.execute("DELETE FROM bm25_tokens WHERE chunk_id IN (SELECT id FROM chunks WHERE doc_id=?)", (doc_id,))
        con.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        con.execute("DELETE FROM pages WHERE doc_id=?", (doc_id,))
    else:
        doc_id = con.execute(
            "INSERT INTO documents(kind,slug,title,short_name,jurisdiction,doc_type,source_url,sha256,retrieved,notes) "
            "VALUES ('book',?,?,?,?,?,?,?,date('now'),?)",
            (BOOK_SLUG, BOOK_TITLE, "Bhumbak", "Punjab", "book", "private copy (owner's PDF)", pdf_sha256,
             "Primary source. Privately published reference book, not an official notification."),
        ).lastrowid
    stats = {"pages": 0, "chunks": 0, "labels_verified": 0, "empty_pages": 0, "failed_lines": 0}
    for f in sorted(ocr_dir.glob("page_*.json")):
        rec = json.loads(f.read_text())
        p = rec["pdf_page"]
        lines = [ln["text"] for ln in rec["lines"] if ln["text"]]
        label, src = detect_printed_label(lines, p)
        clean = clean_ocr(rec["text_raw"])
        front = int(p < FIRST_BODY_PDF_PAGE)
        failed = rec.get("failed_lines", 0)
        quality = "empty" if len(clean) < 40 else ("partial" if failed else "ok")
        con.execute(
            "INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (doc_id, p, label, src, rec["text_raw"], clean, rec["n_lines"], failed, rec.get("recovered_psm13", 0),
             quality, front, rec.get("engine"), rec.get("image_sha256")),
        )
        stats["pages"] += 1
        stats["labels_verified"] += label is not None
        stats["empty_pages"] += quality == "empty"
        stats["failed_lines"] += failed
        if quality == "empty":
            continue
        for i, ch in enumerate(_chunks(clean)):
            cid = hashlib.sha256(f"{BOOK_SLUG}|{p}|{i}|{ch}".encode()).hexdigest()[:16]
            flags = [] if quality == "ok" else ["ocr_partial"]
            if rec.get("recovered_psm13"):
                flags.append("has_psm13_lines")
            con.execute(
                "INSERT INTO chunks(id,doc_id,ordinal,source_type,text,pdf_page_start,pdf_page_end,printed_labels,"
                "section,heading,quality_flags,excluded) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (cid, doc_id, p * 100 + i, "book", ch, p, p, label, None, lines[0][:80] if lines else None,
                 ",".join(flags), front),
            )
            stats["chunks"] += 1
    con.commit()
    return stats
