"""Adversarial Verification Suite for Milestone 1 Ingestion & Chunking.

Conducted by Challenger 2 (challenger_m1_2).
Verifies:
1. Ingestion on temporary in-memory and file-based SQLite databases.
2. Integrity of chunks for Pages 113, 167, 171, 175, 179, 183, 261.
3. Printed labels on chunks match pdf_page - 15.
4. Repaired statutory and survey clauses are intact in created chunks.
5. Absence of corrupted tokens.
6. No orphaned text or truncated sentences in critical clauses.
7. Grounding validation against real ingested chunks.
8. Ingestion idempotence.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
import pytest

from revenue_jarvis import db as dbm
from revenue_jarvis.ingest.book import BODY_OFFSET, ingest_book
from revenue_jarvis.retrieve import Evidence
from revenue_jarvis.answer import validate


REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_SELECTED_DIR = REPO_ROOT / "reports" / "ocr_repair" / "ocr_selected"
TARGET_PAGES = [113, 167, 171, 175, 179, 183, 261]


@pytest.fixture(scope="module")
def memory_db():
    con = dbm.connect(":memory:")
    stats = ingest_book(con, OCR_SELECTED_DIR)
    yield con, stats
    con.close()


@pytest.fixture()
def temp_file_db(tmp_path):
    db_path = tmp_path / "test_ingest.db"
    con = dbm.connect(db_path)
    stats = ingest_book(con, OCR_SELECTED_DIR)
    yield con, stats, db_path
    con.close()


def test_sqlite_integrity_and_foreign_keys(memory_db):
    con, stats = memory_db
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    assert integrity == "ok"
    fk_errors = con.execute("PRAGMA foreign_key_check").fetchall()
    assert len(fk_errors) == 0


def test_printed_labels_match_pdf_page_minus_15(memory_db):
    con, _ = memory_db
    for p in TARGET_PAGES:
        expected_label = str(p - BODY_OFFSET)
        p_row = con.execute("SELECT printed_label, label_source, quality FROM pages WHERE pdf_page=?", (p,)).fetchone()
        assert p_row is not None, f"Page {p} not found in pages table"
        assert p_row["printed_label"] == expected_label, f"Page {p} printed_label mismatch: {p_row['printed_label']} != {expected_label}"
        assert p_row["label_source"] == "ocr_verified"
        assert p_row["quality"] == "ok"

        chunks = con.execute("SELECT id, printed_labels, excluded, quality_flags FROM chunks WHERE pdf_page_start=?", (p,)).fetchall()
        assert len(chunks) > 0, f"Page {p} produced 0 chunks"
        for c in chunks:
            assert c["printed_labels"] == expected_label, f"Chunk {c['id']} printed_labels mismatch: {c['printed_labels']} != {expected_label}"
            assert c["excluded"] == 0, f"Chunk {c['id']} unexpectedly excluded"
            expected_flags = "has_psm13_lines" if p == 179 else ""
            assert c["quality_flags"] == expected_flags, f"Chunk {c['id']} unexpected quality flags: {c['quality_flags']} != {expected_flags}"


def test_page_113_statutory_clauses_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=113 ORDER BY ordinal").fetchall()
    combined_chunks_text = "\n---\n".join(c["text"] for c in chunks)

    # Corrupt tokens must be completely absent
    assert "ABC" not in combined_chunks_text
    assert "SIF" not in combined_chunks_text
    assert "35 © ਤਰਸ" not in combined_chunks_text

    # Section 39 deadline & fine power must be in chunks
    has_s39 = any("ਧਾਰਾ 39" in c["text"] and "ਤਿੰਨ ਮਹੀਨੇ" in c["text"] for c in chunks)
    assert has_s39, "Section 39 3-month reporting deadline missing from Page 113 chunks"

    has_fine = any("ਕਲੈਕਟਰ" in c["text"] and "ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ" in c["text"] for c in chunks)
    assert has_fine, "Collector 5x fine power missing from Page 113 chunks"

    # Section 44 presumption of truth
    has_s44 = any("ਧਾਰਾ 44" in c["text"] and "ਜਮਾਂਬੰਦੀ" in c["text"] and "ਸਚਾਈ ਦੀ ਧਾਰਨਾ" in c["text"] for c in chunks)
    assert has_s44, "Section 44 presumption of truth missing from Page 113 chunks"


def test_page_167_assistant_collector_and_nri_jurisdiction_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=167 ORDER BY ordinal").fetchall()
    combined = "\n---\n".join(c["text"] for c in chunks)

    # Corrupt tokens absent
    for bad in ["TI ਪਹਿਲਾ", "set ane", "doe", "ਮਾਲ mere"]:
        assert bad not in combined

    # Assistant collector designation
    assert any("ਦਰਜਾ ਪਹਿਲਾ" in c["text"] for c in chunks)
    # DRO NRI jurisdiction
    assert any("ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ" in c["text"] and "1.12.2008" in c["text"] for c in chunks)
    # Forum
    assert any("ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ" in c["text"] for c in chunks)


def test_page_171_sanction_clause_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=171 ORDER BY ordinal").fetchall()
    combined = "\n---\n".join(c["text"] for c in chunks)

    assert "OO Ono" not in combined
    assert any("ਇਸ ਨੂੰ ਮੰਜੂਰ" in c["text"] or "ਇਸ ਨੂੰ ਮੰਜ਼ੂਰ" in c["text"] for c in chunks)


def test_page_175_partition_precedent_and_land_measurement_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=175 ORDER BY ordinal").fetchall()
    combined = "\n---\n".join(c["text"] for c in chunks)

    assert "੭30 ਕਲੀ 17 ਨ 9" not in combined

    # Precedent citation
    has_precedent = any("ਰਾਜਪਾਲ ਸਿੰਘ" in c["text"] and "ਮੱਖਣ ਸਿੰਘ" in c["text"] and "2008" in c["text"] and "132" in c["text"] for c in chunks)
    assert has_precedent, "Precedent citation missing from Page 175 chunks"

    # Land measurement
    assert any("230 ਕਨਾਲ" in c["text"] and "10 ਮਰਲੇ" in c["text"] for c in chunks)

    # Filing date
    assert any("12.8.2019" in c["text"] for c in chunks)


def test_page_179_two_karam_pathway_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=179 ORDER BY ordinal").fetchall()
    combined = "\n---\n".join(c["text"] for c in chunks)

    assert "€ ਕਰਮਾਂ" not in combined
    assert any("ਦੋ ਕਰਮਾਂ ਦਾ ਰਸਤਾ" in c["text"] for c in chunks)
    assert any("ਕਰਮਾਂ ਦਾ ਰਸਤਾ" in c["text"] for c in chunks)


def test_page_183_registration_exemption_and_s150_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=183 ORDER BY ordinal").fetchall()
    combined = "\n---\n".join(c["text"] for c in chunks)

    assert "Se ita" not in combined
    # Registration exemption
    assert any("ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ" in c["text"] and "ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਐਕਟ, 1908" in c["text"] for c in chunks)
    # Section 150 unauthorized possession
    assert any("150" in c["text"] and "ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾ" in c["text"] for c in chunks)


def test_page_261_standard_karam_and_jarib_links_in_chunks(memory_db):
    con, _ = memory_db
    chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=261 ORDER BY ordinal").fetchall()
    combined = "\n---\n".join(c["text"] for c in chunks)

    assert "cc ਇੰਜ" not in combined
    assert "fig" not in combined

    # 66 inch karam
    assert any("66 ਇੰਚ" in c["text"] for c in chunks)
    # 8 and 7 links
    assert any("8 ਕੜੀਆਂ" in c["text"] and "7 ਕੜੀਆਂ" in c["text"] for c in chunks)
    # 60 and 54 inch conversions
    assert any("60 ਇੰਚ" in c["text"] and "54 ਇੰਚ" in c["text"] for c in chunks)


def test_critical_clauses_not_truncated_or_split(memory_db):
    """Verify that none of the critical statutory and measurement clauses are split across chunk borders."""
    con, _ = memory_db
    critical_clauses = [
        # (page, complete phrase that must exist intact within at least one chunk)
        (113, "ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ"),
        (113, "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ"),
        (113, "ਕੇਵਲ ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ, 1887 ਦੀ ਧਾਰਾ 44 ਤਹਿਤ ਜਮਾਂਬੰਦੀ ਦੇ ਇੰਦਰਾਜ਼ਾਂ ਨੂੰ ਹੀ ਪ੍ਰਾਪਤ ਹੈ"),
        (167, "ਦਰਜਾ ਪਹਿਲਾ"),
        (167, "ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ ਨੂੰ ਨੋਟੀਫਿਕੇਸ਼ਨ ਮਿਤੀ 1.12.2008"),
        (167, "ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ ਪੇਸ਼ ਕਰ ਸਕਦਾ ਹੈ"),
        (171, "ਮਾਲ ਅਫ਼ਸਰ ਪਾਸੋਂ ਇਸ ਨੂੰ ਮੰਜੂਰ ਕਰਵਾ ਸਕਦੀਆਂ ਹਨ"),
        (175, "2008 (1) ਐਲ. ਏ. ਆਰ. 132 (ਐਫ਼. ਸੀ. ਪੰਜਾਬ)"),
        (175, "230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ"),
        (179, "ਦੋ ਕਰਮਾਂ ਦਾ ਰਸਤਾ"),
        (183, "ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਐਕਟ, 1908 ਦੀ ਧਾਰਾ 17 ਦੀ ਉਪ ਧਾਰਾ 2 ਕਲਾਜ਼ (viii) ਮੁਤਾਬਿਕ ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਤੋਂ ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ"),
        (183, "ਧਾਰਾ 150 ਤਹਿਤ ਮਾਲ ਅਫ਼ਸਰ ਨੂੰ ਇਸ ਨਾਜਾਇਜ਼ ਕਬਜ਼ੇ ਨੂੰ ਖ਼ਾਲੀ ਕਰਵਾਉਣ"),
        (261, "ਇੱਕ ਸਟੈਂਡਰਡ ਕਰਮ 66 ਇੰਚ ਦੀ ਹੈ"),
        (261, "ਇੱਕ ਕਰਮ ਵਿੱਚ 8 ਕੜੀਆਂ ਅਤੇ ਛੋਟੀ ਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ 7 ਕੜੀਆਂ ਹੁੰਦੀਆਂ ਹਨ"),
        (261, "(5) 60 ਇੰਚ ਅਤੇ (6) 54 ਇੰਚ"),
    ]

    for p, clause in critical_clauses:
        chunks = con.execute("SELECT id, text FROM chunks WHERE pdf_page_start=?", (p,)).fetchall()
        found = False
        for c in chunks:
            norm_c = " ".join(c["text"].split())
            if clause in norm_c:
                found = True
                break
        assert found, f"Clause '{clause}' on page {p} was truncated or severed across chunk boundaries!"


def test_grounding_validation_with_real_ingested_chunks(memory_db):
    """Verify that grounding validation accepts answers supported by real ingested chunks."""
    con, _ = memory_db

    def reply(claim, quote, sid="B1"):
        return {
            "status": "answered",
            "claims": [{"text": claim, "source_ids": [sid], "support": [{"source_id": sid, "quote": quote}]}],
        }

    # Page 113 - Collector fine
    c113 = con.execute("SELECT id, text, printed_labels FROM chunks WHERE pdf_page_start=113 AND text LIKE '%ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ%'").fetchone()
    ev113 = Evidence(sid="B1", chunk_id=c113["id"], source_type="book", text=c113["text"], doc_title="Bhumbak", short_name="Bhumbak", pdf_page=113, printed_page=c113["printed_labels"], locator_verified=True)
    q113 = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ"
    cl113 = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।"
    ans, _ = validate(reply(cl113, q113), [ev113])
    assert ans.status == "answered"

    # Page 261 - Karam & Jarib
    c261 = con.execute("SELECT id, text, printed_labels FROM chunks WHERE pdf_page_start=261 AND text LIKE '%8 ਕੜੀਆਂ%'").fetchone()
    ev261 = Evidence(sid="B1", chunk_id=c261["id"], source_type="book", text=c261["text"], doc_title="Bhumbak", short_name="Bhumbak", pdf_page=261, printed_page=c261["printed_labels"], locator_verified=True)
    q261 = "66 ਇੰਚ\nਦੀ ਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ ਇੱਕ ਕਰਮ ਵਿੱਚ 8 ਕੜੀਆਂ ਅਤੇ ਛੋਟੀ\nਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ 7 ਕੜੀਆਂ ਹੁੰਦੀਆਂ ਹਨ"
    cl261 = "66 ਇੰਚ ਦੀ ਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ ਇੱਕ ਕਰਮ ਵਿੱਚ 8 ਕੜੀਆਂ ਅਤੇ ਛੋਟੀ ਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ 7 ਕੜੀਆਂ ਹੁੰਦੀਆਂ ਹਨ।"
    ans, _ = validate(reply(cl261, q261), [ev261])
    assert ans.status == "answered"


def test_ingestion_idempotence(temp_file_db):
    """Running ingest_book a second time on the same DB produces identical row counts."""
    con, stats1, _ = temp_file_db
    stats2 = ingest_book(con, OCR_SELECTED_DIR)
    assert stats1 == stats2

    chunks_count = con.execute("SELECT count(*) FROM chunks").fetchone()[0]
    pages_count = con.execute("SELECT count(*) FROM pages").fetchone()[0]
    assert chunks_count == stats1["chunks"]
    assert pages_count == stats1["pages"]
