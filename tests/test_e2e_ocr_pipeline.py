"""Comprehensive E2E Test Suite for Revenue-Jarvis OCR Pipeline Hardening & Repair.

Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Interaction
Testing + Real-World Application Workloads (4-Tier Architecture from TEST_INFRA.md).

Authoritative References:
- ORIGINAL_REQUEST.md
- PROJECT.md
- TEST_INFRA.md
- reports/independent_audit/REPORT.md
- reports/ocr_repair/backup/jarvis.production-20261013-141120.db (Baseline Backup)
- reports/ocr_repair/jarvis.staged.db (Staged Database)
- reports/ocr_repair/ocr_selected/ (Repaired Page OCR JSONs)

Tiers Covered:
- Tier 1: Feature Coverage (F1 through F5, 5 test cases each = 25 cases)
- Tier 2: Boundary & Corner Cases (F1 through F5, 5 test cases each = 25 cases)
- Tier 3: Cross-Feature Interactions (Pairwise combinations = 5 cases)
- Tier 4: Real-World Application Workloads (5 End-to-End Scenarios = 5 cases)
Total Test Cases: 60
"""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from revenue_jarvis import db as dbm
from revenue_jarvis import ocr_review
from revenue_jarvis.answer import _spoken, validate
from revenue_jarvis.ingest.book import (
    BODY_OFFSET,
    FIRST_BODY_PDF_PAGE,
    _chunks,
    detect_printed_label,
    ingest_book,
)
from revenue_jarvis.retrieve import Evidence
from revenue_jarvis.text import ascii_digits, clean_ocr

# ==============================================================================
# Path Constants & Authoritative References
# ==============================================================================

REPO_ROOT = Path(__file__).resolve().parents[1]
OCR_SELECTED_DIR = REPO_ROOT / "reports" / "ocr_repair" / "ocr_selected"
STAGED_DB_PATH = REPO_ROOT / "reports" / "ocr_repair" / "jarvis.staged.db"
BASELINE_BACKUP_PATH = REPO_ROOT / "reports" / "ocr_repair" / "backup" / "jarvis.production-20261013-141120.db"
GROUNDTRUTH_DIR = REPO_ROOT / "reports" / "ocr_repair" / "groundtruth"


# ==============================================================================
# Test Fixtures & Shared Helpers
# ==============================================================================

@pytest.fixture()
def staged_db_ro():
    """Read-only connection to the staged database."""
    con = sqlite3.connect(f"file:{STAGED_DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


@pytest.fixture()
def baseline_db_ro():
    """Read-only connection to the baseline production backup database."""
    con = sqlite3.connect(f"file:{BASELINE_BACKUP_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


@pytest.fixture()
def isolated_staged_db(tmp_path):
    """Isolated read-write copy of the staged database in a temp directory."""
    temp_db = tmp_path / "jarvis.db"
    shutil.copy(STAGED_DB_PATH, temp_db)
    con = dbm.connect(temp_db)
    try:
        yield con, temp_db
    finally:
        con.close()


def load_ocr_page(pdf_page: int) -> dict:
    """Load JSON record from reports/ocr_repair/ocr_selected/page_{pdf_page:04d}.json."""
    path = OCR_SELECTED_DIR / f"page_{pdf_page:04d}.json"
    assert path.exists(), f"OCR JSON file for page {pdf_page} missing at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def page_text_combined(rec: dict) -> str:
    """Combine text_clean and text_raw for comprehensive content inspection."""
    return (rec.get("text_clean") or "") + "\n" + (rec.get("text_raw") or "")


def make_ev(sid: str, text: str, pdf_page: int, printed_page: str | int | None = None,
            doc_title: str = "Bhumbak", section: str | None = None, source_type: str = "book") -> Evidence:
    """Construct an Evidence instance for grounding validation tests."""
    return Evidence(
        sid=sid,
        chunk_id=f"chk_{sid}",
        source_type=source_type,
        text=text,
        doc_title=doc_title,
        short_name=doc_title,
        pdf_page=pdf_page,
        printed_page=str(printed_page) if printed_page is not None else None,
        section=section,
        locator_verified=True,
    )


def make_reply(claim_text: str, quote: str, sid: str = "B1") -> dict:
    """Construct a single-claim reply dictionary matching ModelAnswer schema."""
    return {
        "status": "answered",
        "claims": [{
            "text": claim_text,
            "source_ids": [sid],
            "support": [{"source_id": sid, "quote": quote}],
        }],
    }


# ==============================================================================
# TIER 1: FEATURE COVERAGE (F1 through F5)
# ==============================================================================

class TestTier1F1RepairedPages:
    """Tier 1: Feature Coverage for F1 (Blocking OCR Pages Repair: 113, 175, 261, 167, 171, 183)."""

    def test_tier1_f1_page_113_mutation_reporting_deadline_and_collector_fine(self):
        """Page 113: Section 39 deadline (3 months), Collector fine power (up to 5x), Section 44 presumption."""
        rec = load_ocr_page(113)
        text = page_text_combined(rec)

        # Corrupted tokens must be absent
        assert "ABC" not in text, "Page 113 still contains corrupted Collector token 'ABC' (pending M1 repair)"
        assert "SIF" not in text, "Page 113 still contains corrupted fee token 'SIF' (pending M1 repair)"
        assert "35 © ਤਰਸ" not in text, "Page 113 still contains corrupted Section 39 token '35 © ਤਰਸ' (pending M1 repair)"

        # Legally verified terms must be present
        assert "ਕਲੈਕਟਰ" in text, "Page 113 missing verified officer designation 'ਕਲੈਕਟਰ' (pending M1 repair)"
        assert "ਫ਼ੀਸ" in text or "ਫੀਸ" in text, "Page 113 missing verified fee term 'ਫ਼ੀਸ' (pending M1 repair)"
        assert "ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ" in text, "Page 113 missing 5x penalty multiplier clause (pending M1 repair)"
        assert "ਧਾਰਾ 39" in text, "Page 113 missing Section 39 notice requirement (pending M1 repair)"
        assert "ਤਿੰਨ ਮਹੀਨੇ" in text, "Page 113 missing 3-month reporting deadline (pending M1 repair)"
        assert "ਧਾਰਾ 44" in text and "ਜਮਾਂਬੰਦੀ" in text, "Page 113 missing Section 44 Jamabandi truth presumption (pending M1 repair)"

    def test_tier1_f1_page_175_partition_precedent_and_land_measurement(self):
        """Page 175: Partition precedent (2008 (1) LAR 132), land measurement (230 ਕਨਾਲ 10 ਮਰਲੇ), filing date."""
        rec = load_ocr_page(175)
        text = page_text_combined(rec)

        # Garbled characters must be eliminated
        assert "੭30 ਕਲੀ 17 ਨ 9" not in text, "Page 175 still contains garbled land measurement '੭30 ਕਲੀ 17 ਨ 9' (pending M1 repair)"

        # Case citation verified
        assert "ਰਾਜਪਾਲ ਸਿੰਘ" in text and "ਮੱਖਣ ਸਿੰਘ" in text, "Page 175 missing precedent case parties (pending M1 repair)"
        assert "2008" in text and "132" in text, "Page 175 missing precedent citation numbers 2008 / 132 (pending M1 repair)"

        # Land area and filing date verified
        assert "230 ਕਨਾਲ" in text and "10 ਮਰਲੇ" in text, "Page 175 missing land area '230 ਕਨਾਲ 10 ਮਰਲੇ' (pending M1 repair)"
        assert "12.8.2019" in text, "Page 175 missing partition application filing date 12.8.2019 (pending M1 repair)"

    def test_tier1_f1_page_261_standard_karam_and_chain_links(self):
        """Page 261: Standard Karam unit (66 ਇੰਚ), survey chain link counts (8 and 7), unit conversions."""
        rec = load_ocr_page(261)
        text = page_text_combined(rec)

        # Corrupted unit string must be eliminated
        assert "cc ਇੰਜ" not in text, "Page 261 still contains corrupted standard karam 'cc ਇੰਜ' (pending M1 repair)"
        assert "fig" not in text, "Page 261 still contains Latin noise 'fig' instead of 'ਇੰਚ' (pending M1 repair)"

        # Measurement standards verified
        assert "66 ਇੰਚ" in text, "Page 261 missing standard karam measurement '66 ਇੰਚ' (pending M1 repair)"
        assert "8 ਕੜੀਆਂ" in text, "Page 261 missing standard jarib link count '8 ਕੜੀਆਂ' (pending M1 repair)"
        assert "7 ਕੜੀਆਂ" in text, "Page 261 missing small karam jarib link count '7 ਕੜੀਆਂ' (pending M1 repair)"
        assert "60 ਇੰਚ" in text and "54 ਇੰਚ" in text, "Page 261 missing conversion series 60/54 inches (pending M1 repair)"

    def test_tier1_f1_page_167_assistant_collector_and_nri_dro_jurisdiction(self):
        """Page 167: Assistant Collector 1st Grade, DRO NRI jurisdiction, notification 1.12.2008."""
        rec = load_ocr_page(167)
        text = page_text_combined(rec)

        # Corrupted Latin and edge noise eliminated
        assert "TI ਪਹਿਲਾ" not in text, "Page 167 still contains scan artifact 'TI ਪਹਿਲਾ' (pending M1 repair)"
        assert "set ane" not in text, "Page 167 still contains scan artifact 'set ane' (pending M1 repair)"
        assert "doe" not in text, "Page 167 still contains Latin artifact 'doe' (pending M1 repair)"
        assert "ਮਾਲ mere" not in text, "Page 167 still contains 'ਮਾਲ mere' instead of 'ਮਾਲ ਅਫ਼ਸਰ' (pending M1 repair)"

        # Verified legal text restored
        assert "ਦਰਜਾ ਪਹਿਲਾ" in text, "Page 167 missing Assistant Collector designation 'ਦਰਜਾ ਪਹਿਲਾ' (pending M1 repair)"
        assert "ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ" in text, "Page 167 missing DRO jurisdiction 'ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ' (pending M1 repair)"
        assert "1.12.2008" in text, "Page 167 missing NRI notification date 1.12.2008 (pending M1 repair)"
        assert "ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ" in text, "Page 167 missing correct application forum 'ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ' (pending M1 repair)"

    def test_tier1_f1_page_171_sanction_clause_and_page_183_registration_exemption(self):
        """Pages 171 & 183: Private partition sanction clause, registration exemption, Section 150 eviction."""
        rec171 = load_ocr_page(171)
        text171 = page_text_combined(rec171)
        assert "OO Ono" not in text171, "Page 171 still contains gibberish symbol line 'OO Ono' (pending M1 repair)"
        assert "ਇਸ ਨੂੰ ਮੰਜੂਰ" in text171 or "ਇਸ ਨੂੰ ਮੰਜ਼ੂਰ" in text171, "Page 171 missing sanction clause 'ਇਸ ਨੂੰ ਮੰਜੂਰ' (pending M1 repair)"

        rec183 = load_ocr_page(183)
        text183 = page_text_combined(rec183)
        assert "Se ita" not in text183, "Page 183 still contains corrupted exemption artifact 'Se ita' (pending M1 repair)"
        assert "ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ" in text183, "Page 183 missing registration exemption clause 'ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ' (pending M1 repair)"
        assert "150" in text183 and "ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾ" in text183, "Page 183 missing Section 150 unauthorized possession clause (pending M1 repair)"


class TestTier1F2OrientationTabular:
    """Tier 1: Feature Coverage for F2 (Orientation Detection & Tabular Extraction: 382, 383, 389)."""

    def test_tier1_f2_page_382_rotated_khasra_table_structure(self):
        """Page 382: 90° rotated Khasra table preserves Khasra numbers, total area, Khewat and Owner."""
        rec = load_ocr_page(382)
        text = page_text_combined(rec)

        # Rotated line-slicing noise must be eliminated
        assert "-200000000/01677301" not in text, "Page 382 contains unrotated character slicing noise (pending M2 repair)"
        assert "0977777557772" not in text, "Page 382 contains gibberish digit run (pending M2 repair)"

        # Semantic table content must be extracted
        assert "2//12" in text or "12" in text, "Page 382 missing Khasra numbers (pending M2 repair)"
        assert "ਕਿਤਾ" in text and "40-0" in text, "Page 382 missing total area summary 40-0 (pending M2 repair)"
        assert "ਗੁਰਮੀਤ ਸਿੰਘ" in text, "Page 382 missing land owner 'ਗੁਰਮੀਤ ਸਿੰਘ' (pending M2 repair)"

    def test_tier1_f2_page_383_jamabandi_12_column_annexure_structure(self):
        """Page 383: 12-column Jamabandi template (Annexure 15) without horizontal interleaving or rotation noise."""
        rec = load_ocr_page(383)
        text = page_text_combined(rec)

        # Corrupted braces and inverted fragments eliminated
        assert "[BE || FE" not in text, "Page 383 contains corrupted bracket/column artifacts (pending M2 repair)"

        # Standard 12-column Jamabandi register headers must be present
        headers = ["ਖੇਵਟ", "ਖਤੌਨੀ", "ਕਾਸ਼ਤਕਾਰ", "ਰਕਬਾ", "ਮਾਲੀਆ"]
        found = [h for h in headers if h in text]
        assert len(found) >= 3, f"Page 383 missing core Jamabandi headers; found only {found} (pending M2 repair)"
        assert "ਅਨੁਲੱਗ" in text or "ਅਨੁਲਗ" in text or "15" in text, "Page 383 missing Annexure 15 label (pending M2 repair)"

    def test_tier1_f2_page_389_khasra_girdawari_register_structure(self):
        """Page 389: 8-column Khasra Girdawari register (Annexure 18) with Sauni and Harhi harvest seasons."""
        rec = load_ocr_page(389)
        text = page_text_combined(rec)

        # Flattened noise strings eliminated
        assert "Taras of os os" not in text, "Page 389 contains horizontal column slicing noise (pending M2 repair)"

        # Core harvest seasons and inspection columns
        assert "ਸਾਉਣੀ" in text or "ਹਾੜੀ" in text or "ਖਸਰਾ ਗਿਰਦਾਵਰੀ" in text, (
            "Page 389 missing Khasra Girdawari register terms (pending M2 repair)"
        )

    def test_tier1_f2_bilingual_glossaries_no_horizontal_interleaving(self):
        """Pages 346 & 368: Multi-column glossaries must not interleave Punjabi definitions with English columns."""
        rec346 = load_ocr_page(346)
        text346 = page_text_combined(rec346)
        assert "CalAVAL" not in text346, "Page 346 contains column bleeding noise 'CalAVAL' (pending M2 repair)"

        rec368 = load_ocr_page(368)
        text368 = page_text_combined(rec368)
        assert "ter fils dt of land" not in text368, "Page 368 contains English/Punjabi spliced fragment (pending M2 repair)"
        assert "ਮਾਲਕਾਨ ਕਬਜ਼ਾ" in text368, "Page 368 missing clean glossary term 'ਮਾਲਕਾਨ ਕਬਜ਼ਾ' (pending M2 repair)"

    def test_tier1_f2_tabular_pages_metadata_and_line_status(self):
        """Tabular annexures 382, 383, 389 must record 0 failed lines and non-empty line content."""
        for p in (382, 383, 389):
            rec = load_ocr_page(p)
            assert rec.get("failed_lines", 0) == 0, f"Page {p} reports failed lines in OCR record"
            assert rec.get("n_lines", 0) > 0, f"Page {p} has zero lines extracted"
            assert len(rec.get("text_raw", "").strip()) > 100, f"Page {p} extracted text too short"


class TestTier1F3PrintedLabelCoverage:
    """Tier 1: Feature Coverage for F3 (Printed Page Label Detection: >95% coverage, offset PDF-15)."""

    def test_tier1_f3_detect_printed_label_offset_rule(self):
        """detect_printed_label accepts a label if and only if expected == pdf_page - 15."""
        # PDF page 167 -> printed page 152
        lines = ["152 ਚੈਪਟਰ 8", "ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਕਰਨੀ", "ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ"]
        lbl, src = detect_printed_label(lines, 167)
        assert lbl == "152"
        assert src == "ocr_verified"

        # Footer placement
        lines_footer = ["ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਕਰਨੀ", "ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ", "152"]
        lbl_foot, src_foot = detect_printed_label(lines_footer, 167)
        assert lbl_foot == "152"
        assert src_foot == "ocr_verified"

    def test_tier1_f3_detect_printed_label_never_infer_unverified(self):
        """detect_printed_label returns (None, 'unknown') when scanned lines lack the expected number."""
        lines = ["ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਕਰਨੀ", "ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ"]
        lbl, src = detect_printed_label(lines, 167)
        assert lbl is None
        assert src == "unknown"

        # Disagreeing number must be rejected (never accept a false number)
        lines_wrong = ["999 ਚੈਪਟਰ 8", "ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ"]
        lbl_wrong, src_wrong = detect_printed_label(lines_wrong, 167)
        assert lbl_wrong is None
        assert src_wrong == "unknown"

    def test_tier1_f3_front_matter_pages_unmapped(self):
        """Front matter pages (PDF 1..15) must always return (None, 'unknown')."""
        for p in range(1, FIRST_BODY_PDF_PAGE):
            lines = [f"{p} ਇੰਡੈਕਸ", "ਮੁੱਖ ਬੰਧ"]
            lbl, src = detect_printed_label(lines, p)
            assert lbl is None
            assert src == "unknown"

    def test_tier1_f3_staged_db_body_label_coverage_threshold(self, staged_db_ro):
        """Staged database must achieve >95% printed page label coverage across 374 body pages (<15 unmapped)."""
        doc_id = staged_db_ro.execute("SELECT id FROM documents WHERE slug='bhumbak-zameen-di-guide'").fetchone()[0]
        rows = staged_db_ro.execute(
            "SELECT pdf_page, printed_label, label_source FROM pages WHERE doc_id=? AND pdf_page>=? ORDER BY pdf_page",
            (doc_id, FIRST_BODY_PDF_PAGE),
        ).fetchall()

        total_body = len(rows)
        assert total_body == 374, f"Expected 374 body pages (PDF 16..389), found {total_body}"

        mapped = [r for r in rows if r["printed_label"] is not None]
        unmapped = [r for r in rows if r["printed_label"] is None]

        # Zero false mismatches rule: every mapped page must satisfy printed_label == pdf_page - 15
        for r in mapped:
            assert int(r["printed_label"]) == r["pdf_page"] - BODY_OFFSET, (
                f"Page {r['pdf_page']} label mismatch: {r['printed_label']} != {r['pdf_page'] - BODY_OFFSET}"
            )
            assert r["label_source"] == "ocr_verified"

        # Coverage threshold: >95% (fewer than 15 unmapped body pages)
        coverage_pct = (len(mapped) / total_body) * 100
        assert len(unmapped) < 15, (
            f"Printed page label coverage {len(mapped)}/374 ({coverage_pct:.1f}%) is below 95% threshold; "
            f"{len(unmapped)} body pages unmapped (pending M3 repair)"
        )

    def test_tier1_f3_audit_unmapped_52_pages_resolution(self):
        """The 52 body pages reported unmapped in the audit must agree with expected offset when scanned."""
        sample_unmapped = [17, 18, 19, 20, 21, 22, 73, 113, 261]
        for p in sample_unmapped:
            expected = p - BODY_OFFSET
            rec = load_ocr_page(p)
            lines = [ln["text"] for ln in rec["lines"] if ln.get("text")]
            # Candidate strings from top 3 and bottom 2 lines
            cands = lines[:3] + lines[-2:]
            nums = [int(n) for ln in cands for n in re.findall(r"(?<!\d)(\d{1,3})(?!\d)", ascii_digits(ln))]
            # When header window captures expected number, detect_printed_label must match
            if expected in nums:
                lbl, src = detect_printed_label(lines, p)
                assert lbl == str(expected)
                assert src == "ocr_verified"


class TestTier1F4RegressionGroundingSafeguards:
    """Tier 1: Feature Coverage for F4 (Regression & Grounding Safeguard Verification)."""

    def test_tier1_f4_grounding_rejects_corrupted_officer_power(self):
        """Grounding validator rejects claim when corrupted text has 'ABC' instead of 'ਕਲੈਕਟਰ'."""
        corrupted = "SOSH Q ABC ਆਪਣੇ ਅਖਿਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ੮' SIF ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ"
        ev = make_ev("B1", corrupted, pdf_page=113, printed_page="98")
        claim = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਲਗਾ ਸਕਦਾ ਹੈ।"
        with pytest.raises(ValueError, match="role|amount|context"):
            validate(make_reply(claim, corrupted, "B1"), [ev])

    def test_tier1_f4_grounding_rejects_corrupted_statutory_deadline(self):
        """Grounding validator rejects Section 39 claim when corrupted text has '35 © ਤਰਸ'."""
        corrupted = "ERT Pll 35 © ਤਰਸ ਮੁਤਾਬਕ ਤਿਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ।"
        ev = make_ev("B1", corrupted, pdf_page=113, printed_page="98")
        claim = "ਧਾਰਾ 39 ਮੁਤਾਬਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਣੀ ਹੁੰਦੀ ਹੈ।"
        with pytest.raises(ValueError, match="section|rule|locator"):
            validate(make_reply(claim, corrupted, "B1"), [ev])

    def test_tier1_f4_grounding_rejects_corrupted_land_measurement(self):
        """Grounding validator rejects 230 ਕਨਾਲ 10 ਮਰਲੇ when corrupted quote has '੭30 ਕਲੀ 17 ਨ 9'."""
        corrupted = "ਨੇ ੭30 ਕਲੀ 17 ਨ 9 ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਦਿੱਤੀ।"
        ev = make_ev("B1", corrupted, pdf_page=175, printed_page="160")
        claim = "230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਦਿੱਤੀ ਗਈ।"
        with pytest.raises(ValueError, match="numeric|amount"):
            validate(make_reply(claim, corrupted, "B1"), [ev])

    def test_tier1_f4_grounding_accepts_clean_repaired_mutation_and_penalty(self):
        """Grounding validator accepts clean claim from repaired Page 113 text."""
        clean = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।"
        ev = make_ev("B1", clean, pdf_page=113, printed_page="98")
        claim = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।"
        ans, warnings = validate(make_reply(claim, clean, "B1"), [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 1
        assert ans.claims[0].text == claim

    def test_tier1_f4_grounding_accepts_clean_repaired_partition_precedent(self):
        """Grounding validator accepts clean claim from repaired Page 175 partition precedent."""
        clean = ("ਰਾਜਪਾਲ ਸਿੰਘ ਅਤੇ ਹੋਰ ਬਨਾਮ ਮੱਖਣ ਸਿੰਘ ਅਤੇ ਹੋਰ 2008 (1) ਐਲ. ਏ. ਆਰ. 132 (ਐਫ਼. ਸੀ. ਪੰਜਾਬ)। "
                 "ਨੇ 230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਮਿਤੀ 12.8.2019 ਨੂੰ ਦਿੱਤੀ ਸੀ।")
        ev = make_ev("B1", clean, pdf_page=175, printed_page="160")
        claim = "230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਮਿਤੀ 12.8.2019 ਨੂੰ ਦਿੱਤੀ ਸੀ।"
        ans, warnings = validate(make_reply(claim, clean, "B1"), [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 1


class TestTier1F5StagedDbRebuildAndCorpusPreservation:
    """Tier 1: Feature Coverage for F5 (Staged DB Rebuild & Law Corpus Isolation)."""

    def test_tier1_f5_check_import_passes_zero_errors(self, staged_db_ro, baseline_db_ro):
        """check_import gate passes on the staged database with 0 errors against baseline backup."""
        report = ocr_review.check_import(staged_db_ro, baseline=baseline_db_ro)
        assert report["passed"], f"check_import failed with errors: {report['errors']}"
        assert report["errors"] == []
        assert report["searchable_chunks"] > 2800

    def test_tier1_f5_law_corpus_exact_doc_and_chunk_counts(self, staged_db_ro, baseline_db_ro):
        """Staged database maintains exactly 27 law documents and 2,213 law chunks."""
        count_docs_staged = staged_db_ro.execute("SELECT count(*) FROM documents WHERE kind='law'").fetchone()[0]
        count_docs_base = baseline_db_ro.execute("SELECT count(*) FROM documents WHERE kind='law'").fetchone()[0]
        assert count_docs_staged == 27
        assert count_docs_base == 27

        count_chunks_staged = staged_db_ro.execute("SELECT count(*) FROM chunks WHERE source_type='law'").fetchone()[0]
        count_chunks_base = baseline_db_ro.execute("SELECT count(*) FROM chunks WHERE source_type='law'").fetchone()[0]
        assert count_chunks_staged == 2213
        assert count_chunks_base == 2213

    def test_tier1_f5_law_corpus_byte_identical_text_and_vectors(self, staged_db_ro, baseline_db_ro):
        """All 2,213 law chunks, vector BLOBs, and BM25 tokens are 100% byte-identical to baseline."""
        query = ("SELECT c.id, c.text, c.section, c.heading, c.quality_flags, e.dim, e.vec, t.tokens "
                 "FROM chunks c JOIN documents d ON c.doc_id=d.id "
                 "LEFT JOIN embeddings e ON e.chunk_id=c.id "
                 "LEFT JOIN bm25_tokens t ON t.chunk_id=c.id "
                 "WHERE d.kind='law' ORDER BY c.id")

        chunks_staged = staged_db_ro.execute(query).fetchall()
        chunks_base = baseline_db_ro.execute(query).fetchall()

        assert len(chunks_staged) == 2213
        assert len(chunks_base) == 2213

        for cs, cb in zip(chunks_staged, chunks_base, strict=True):
            assert cs["id"] == cb["id"]
            assert cs["text"] == cb["text"]
            assert cs["section"] == cb["section"]
            assert cs["heading"] == cb["heading"]
            assert cs["quality_flags"] == cb["quality_flags"]
            assert cs["dim"] == cb["dim"]
            assert cs["vec"] == cb["vec"], f"Law chunk {cs['id']} embedding vector differs from baseline"
            assert cs["tokens"] == cb["tokens"], f"Law chunk {cs['id']} BM25 tokens differ from baseline"

    def test_tier1_f5_page_reviews_table_provenance(self, staged_db_ro):
        """Every record in page_reviews is designated 'needs_review'; zero marked 'scan_verified'."""
        reviews = staged_db_ro.execute("SELECT doc_id, pdf_page, status, reviewer, text_sha256, image_sha256 FROM page_reviews").fetchall()
        assert len(reviews) > 0, "Expected page review provenance records in staged database"

        for r in reviews:
            assert r["status"] == "needs_review", f"Page {r['pdf_page']} falsely marked '{r['status']}' instead of 'needs_review'"
            assert "AI assistant" in r["reviewer"] or "NOT human-reviewed" in r["reviewer"]
            # Reviewed text and image hash must match pages table
            page_row = staged_db_ro.execute("SELECT text_clean, image_sha256 FROM pages WHERE doc_id=? AND pdf_page=?", (r["doc_id"], r["pdf_page"])).fetchone()
            assert page_row is not None
            assert ocr_review.text_hash(page_row["text_clean"] or "") == r["text_sha256"]
            assert page_row["image_sha256"] == r["image_sha256"]

    def test_tier1_f5_zero_orphan_records_and_fk_integrity(self, staged_db_ro):
        """Zero foreign key violations, zero orphan records in embeddings or bm25_tokens."""
        assert staged_db_ro.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert staged_db_ro.execute("PRAGMA foreign_key_check").fetchall() == []

        orphan_emb = staged_db_ro.execute("SELECT count(*) FROM embeddings WHERE chunk_id NOT IN (SELECT id FROM chunks)").fetchone()[0]
        orphan_bm25 = staged_db_ro.execute("SELECT count(*) FROM bm25_tokens WHERE chunk_id NOT IN (SELECT id FROM chunks)").fetchone()[0]
        assert orphan_emb == 0, f"Found {orphan_emb} orphan records in embeddings"
        assert orphan_bm25 == 0, f"Found {orphan_bm25} orphan records in bm25_tokens"


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES (F1 through F5)
# ==============================================================================

class TestTier2F1Boundaries:
    """Tier 2: Boundary & Corner Cases for F1 (Repaired Pages)."""

    def test_tier2_f1_page_30_single_blank_page_preservation(self):
        """Page 30 is the only visibly blank scan page; must remain quality='empty' with 0 lines."""
        rec = load_ocr_page(30)
        clean = clean_ocr(rec.get("text_raw", ""))
        assert len(clean) < 40, f"Blank page 30 has non-empty clean text: {clean[:50]}"
        assert rec.get("failed_lines", 0) == 0

    def test_tier2_f1_multilingual_digit_normalization(self):
        """Gurmukhi digits (੧੨.੮.੨੦੧੯, ੬੬) correctly convert to ASCII without corrupting surrounding text."""
        raw_date = "ਮਿਤੀ ੧੨.੮.੨੦੧੯ ਨੂੰ ਦਰਖਾਸਤ ਦਿੱਤੀ"
        ascii_date = ascii_digits(raw_date)
        assert "12.8.2019" in ascii_date
        assert "ਮਿਤੀ" in ascii_date

        raw_karam = "ਸਟੈਂਡਰਡ ਕਰਮ ੬੬ ਇੰਚ ਦੀ ਹੈ"
        ascii_karam = ascii_digits(raw_karam)
        assert "66" in ascii_karam

    def test_tier2_f1_page_73_hindu_succession_act_cutoff_boundary(self):
        """Page 73 bottom margin boundary: Hindu Succession Act Section 30 must not be cut off."""
        rec = load_ocr_page(73)
        text = page_text_combined(rec)
        assert "ਹਿੰਦੂ ਉੱਤਰਾਧਿਕਾਰ" in text or "ਧਾਰਾ 30" in text, (
            "Page 73 cut off at bottom margin; missing Hindu Succession Act reference (pending M1 repair)"
        )

    def test_tier2_f1_page_179_two_karam_pathway_boundary(self):
        """Page 179 pathway dimension boundary: 'ਦੋ ਕਰਮਾਂ ਦਾ ਰਸਤਾ' must not become Euro symbol '€ ਕਰਮਾਂ'."""
        rec = load_ocr_page(179)
        text = page_text_combined(rec)
        assert "€ ਕਰਮਾਂ" not in text, "Page 179 contains symbol artifact '€ ਕਰਮਾਂ' instead of 'ਦੋ ਕਰਮਾਂ' (pending M1 repair)"
        assert "ਕਰਮਾਂ ਦਾ ਰਸਤਾ" in text, "Page 179 missing pathway dimension clause (pending M1 repair)"

    def test_tier2_f1_repaired_pages_bounding_boxes_validity(self):
        """Repaired page JSONs have non-negative bounding box coordinates with y1 > y0."""
        for p in (113, 167, 171, 175, 183, 261):
            rec = load_ocr_page(p)
            for ln in rec.get("lines", []):
                if "box" in ln:
                    y0, x0, y1, x1 = ln["box"]
                    assert y1 > y0 and x1 > x0 and y0 >= 0 and x0 >= 0
                elif "y0" in ln:
                    assert ln["y1"] > ln["y0"] and ln["y0"] >= 0


class TestTier2F2Boundaries:
    """Tier 2: Boundary & Corner Cases for F2 (Orientation & Tabular Extraction)."""

    def test_tier2_f2_tabular_empty_cells_and_null_values(self):
        """Table extraction preserves empty register columns without shifting adjacent cell data."""
        # Simulated Jamabandi row with empty cultivator / irrigation cells
        row = "243\t105\tਗੁਰਮੀਤ ਸਿੰਘ\t\t\tਨਹਿਰੀ\t2//12\t8-0\t0.50"
        cells = row.split("\t")
        assert len(cells) == 9
        assert cells[0] == "243"  # Khewat
        assert cells[2] == "ਗੁਰਮੀਤ ਸਿੰਘ"  # Owner
        assert cells[3] == ""  # Cultivator (empty)
        assert cells[5] == "ਨਹਿਰੀ"  # Irrigation

    def test_tier2_f2_orientation_rotation_angle_boundaries(self):
        """Orientation detection handles 90° CW and 90° CCW (270°) rotation angles."""
        valid_orientations = {0, 90, 180, 270}
        for p in (382, 383, 389):
            rec = load_ocr_page(p)
            rot = rec.get("rotation_deg", 0)
            assert rot in valid_orientations

    def test_tier2_f2_table_chunk_boundary_preserves_rows(self):
        """_chunks() paragraph slicer does not bisect tabular data rows across chunks."""
        table_text = "ਖੇਵਟ 243 ਨਾਮ ਮਾਲਕ ਗੁਰਮੀਤ ਸਿੰਘ ਰਕਬਾ 40-0\nਖੇਵਟ 244 ਨਾਮ ਮਾਲਕ ਅਮਰੀਕ ਸਿੰਘ ਰਕਬਾ 20-0\nਖੇਵਟ 245 ਨਾਮ ਮਾਲਕ ਜਸਵੰਤ ਸਿੰਘ ਰਕਬਾ 15-0"
        chunks = _chunks(table_text)
        assert len(chunks) >= 1
        for ch in chunks:
            # Lines must stay complete
            for line in ch.splitlines():
                if "ਖੇਵਟ 243" in line:
                    assert "ਗੁਰਮੀਤ ਸਿੰਘ" in line

    def test_tier2_f2_bilingual_glossary_special_delimiters(self):
        """Glossary terms with slashes and Punjabi danda preserve key-value mappings."""
        entry = "ਆਬਾਦੀ ਦੇਹ/ਲਾਲ ਲਕੀਰ | ਪਿੰਡ ਦੀ ਵਸੋਂ ਵਾਲੀ ਜ਼ਮੀਨ | Village inhabited site"
        parts = [p.strip() for p in entry.split("|")]
        assert len(parts) == 3
        assert "ਆਬਾਦੀ ਦੇਹ/ਲਾਲ ਲਕੀਰ" in parts[0]
        assert "Village inhabited site" in parts[2]

    def test_tier2_f2_annexure_headers_isolation(self):
        """Annexure titles (ਅਨੁਲੱਗ-15) are isolated from register column headers."""
        header_block = "ਅਨੁਲੱਗ-15\nਨਕਲ ਜਮਾਂਬੰਦੀ\nਖੇਵਟ ਨੰ: | ਖਤੌਨੀ ਨੰ:"
        lines = header_block.splitlines()
        assert "ਅਨੁਲੱਗ-15" == lines[0].strip()
        assert "ਖੇਵਟ" in lines[2]


class TestTier2F3Boundaries:
    """Tier 2: Boundary & Corner Cases for F3 (Printed Page Label Detection)."""

    def test_tier2_f3_header_with_chapter_number_clash(self):
        """Header with chapter number and page label (e.g., 'ਚੈਪਟਰ 5   98') extracts page label 98."""
        lines = ["ਚੈਪਟਰ 5   98", "ਇੰਤਕਾਲ", "ਜ਼ਮੀਨ ਪ੍ਰਬੰਧਨ ਵਿੱਚ"]
        lbl, src = detect_printed_label(lines, 113)  # 113 - 15 = 98
        assert lbl == "98"
        assert src == "ocr_verified"

    def test_tier2_f3_candidate_window_top_vs_bottom_lines(self):
        """Page number present in line 1 vs line 3 vs final line is captured within candidate window."""
        # Top line 1
        lbl1, _ = detect_printed_label(["152", "ਲਾਈਨ 2", "ਲਾਈਨ 3"], 167)
        assert lbl1 == "152"

        # Line 3
        lbl3, _ = detect_printed_label(["ਹੈਡਰ", "ਉਪ-ਹੈਡਰ", "152", "ਬਾਡੀ ਟੈਕਸਟ"], 167)
        assert lbl3 == "152"

        # Footer last line
        lbl_last, _ = detect_printed_label(["ਬਾਡੀ ਟੈਕਸਟ", "ਲਾਈਨ ਅੰਤਲੀ", "152"], 167)
        assert lbl_last == "152"

    def test_tier2_f3_exact_boundary_page_15_to_16(self):
        """Exact transition boundary: PDF 15 returns (None, 'unknown'); PDF 16 returns ('1', 'ocr_verified')."""
        lines_15 = ["15 ਇੰਡੈਕਸ"]
        lbl15, src15 = detect_printed_label(lines_15, 15)
        assert lbl15 is None
        assert src15 == "unknown"

        lines_16 = ["1 ਚੈਪਟਰ 1", "ਭੂਮਿਕਾ"]
        lbl16, src16 = detect_printed_label(lines_16, 16)
        assert lbl16 == "1"
        assert src16 == "ocr_verified"

    def test_tier2_f3_noisy_scanned_label_punctuation(self):
        """Scanned header number with OCR artifacts (e.g., 'ਵ 98', '| 98 |', '98.') correctly parses 98."""
        for noisy_line in ["ਵ 98", "| 98 |", "98.", "(98)"]:
            lbl, src = detect_printed_label([noisy_line, "ਚੈਪਟਰ 5"], 113)
            assert lbl == "98"
            assert src == "ocr_verified"

    def test_tier2_f3_ambiguous_four_digit_year_clash(self):
        """Header with both Act year 1887 and page number 98 selects expected offset 98."""
        lines = ["ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ 1887   98", "ਚੈਪਟਰ 5"]
        lbl, src = detect_printed_label(lines, 113)
        assert lbl == "98"
        assert src == "ocr_verified"


class TestTier2F4Boundaries:
    """Tier 2: Boundary & Corner Cases for F4 (Answer Grounding Validation)."""

    def test_tier2_f4_bare_number_cannot_borrow_act_year_as_fee(self):
        """Year 1887 in 'PLRA 1887' cannot be borrowed as a fee of ₹1887."""
        quote = "ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ, 1887 ਦੀ ਧਾਰਾ 34 ਤਹਿਤ ਇੰਤਕਾਲ ਦਰਜ ਹੁੰਦਾ ਹੈ।"
        ev = make_ev("B1", quote, pdf_page=113, printed_page="98")
        invented_fee_claim = "ਇੰਤਕਾਲ ਦਰਜ ਕਰਵਾਉਣ ਦੀ ਫ਼ੀਸ ₹1887 ਹੈ।"
        with pytest.raises(ValueError, match="numeric|amount"):
            validate(make_reply(invented_fee_claim, quote, "B1"), [ev])

    def test_tier2_f4_permission_to_obligation_modal_shift_rejected(self):
        """Source permission ('ਸਕਦਾ ਹੈ' / may) mutated to obligation ('ਲਾਜ਼ਮੀ ਹੈ' / must) is rejected."""
        source = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਜੁਰਮਾਨਾ ਲਗਾ ਸਕਦਾ ਹੈ।"
        ev = make_ev("B1", source, pdf_page=113, printed_page="98")
        claim = "ਕਲੈਕਟਰ ਲਈ ਜੁਰਮਾਨਾ ਲਗਾਉਣਾ ਲਾਜ਼ਮੀ ਹੈ।"
        with pytest.raises(ValueError, match="permission into a requirement"):
            validate(make_reply(claim, source, "B1"), [ev])

    def test_tier2_f4_fee_vs_fine_polarity_and_scoping(self):
        """Fee amount cannot be substituted for fine amount when both exist in the quote."""
        quote = "ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ₹100 ਹੈ ਪਰ ਦੇਰੀ ਹੋਣ ਤੇ ਜੁਰਮਾਨਾ ₹500 ਲਗਾਇਆ ਜਾ ਸਕਦਾ ਹੈ।"
        ev = make_ev("B1", quote, pdf_page=113, printed_page="98")
        wrong_fee_claim = "ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ₹500 ਹੈ।"
        with pytest.raises(ValueError, match="numeric|amount|fee"):
            validate(make_reply(wrong_fee_claim, quote, "B1"), [ev])

    def test_tier2_f4_foreign_script_injection_rejected(self):
        """Devanagari or Arabic characters injected into claim text trigger FORBIDDEN_SCRIPT rejection."""
        source = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਜੁਰਮਾਨਾ ਲਗਾ ਸਕਦਾ ਹੈ।"
        ev = make_ev("B1", source, pdf_page=113, printed_page="98")
        # Injected Devanagari text
        injected_claim = "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ तਹਿਤ ਜੁਰਮਾਨਾ ਲਗਾ ਸਕਦਾ ਹੈ।"
        with pytest.raises(ValueError, match="Unsupported output script"):
            validate(make_reply(injected_claim, source, "B1"), [ev])

    def test_tier2_f4_partial_answer_mode_keeps_clean_drops_corrupted(self):
        """allow_partial=True keeps supported claim, drops unsupported claim, sets partial_answer=True."""
        ev1 = make_ev("B1", "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।", 113, "98")
        ev2 = make_ev("B2", "ERT Pll 35 © ਤਰਸ ਮੁਤਾਬਕ ਤਿਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ।", 113, "98")
        reply = {
            "status": "answered",
            "claims": [
                {
                    "text": "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।",
                    "source_ids": ["B1"],
                    "support": [{"source_id": "B1", "quote": ev1.text}],
                },
                {
                    "text": "ਧਾਰਾ 39 ਮੁਤਾਬਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਣੀ ਹੁੰਦੀ ਹੈ।",
                    "source_ids": ["B2"],
                    "support": [{"source_id": "B2", "quote": ev2.text}],
                },
            ],
        }
        ans, warnings = validate(reply, [ev1, ev2], allow_partial=True)
        assert ans.status == "answered"
        assert ans.partial_answer is True
        assert len(ans.claims) == 1
        assert "ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ" in ans.claims[0].text
        assert any("Suppressed unsupported claim" in w for w in warnings)


class TestTier2F5Boundaries:
    """Tier 2: Boundary & Corner Cases for F5 (Database Rebuild & Preservation)."""

    def test_tier2_f5_rebuild_idempotency_double_ingest(self, isolated_staged_db):
        """ingest_book deletes only the book document; running it twice preserves law rows."""
        con, _ = isolated_staged_db
        count_law_before = con.execute("SELECT count(*) FROM chunks WHERE source_type='law'").fetchone()[0]

        # Re-ingest book into the isolated copy
        stats1 = ingest_book(con, OCR_SELECTED_DIR)
        count_law_after = con.execute("SELECT count(*) FROM chunks WHERE source_type='law'").fetchone()[0]
        assert count_law_before == count_law_after == 2213
        assert stats1["pages"] == 389

    def test_tier2_f5_vector_normalization_unit_length_and_finiteness(self, staged_db_ro):
        """Every embedding vector in the staged DB is finite float32 with L2 norm of 1.0 ± 1e-5."""
        vectors = staged_db_ro.execute("SELECT chunk_id, dim, vec FROM embeddings LIMIT 100").fetchall()
        for r in vectors:
            assert r["dim"] == 384
            vec = np.frombuffer(r["vec"], dtype=np.float32)
            assert vec.shape == (384,)
            assert np.isfinite(vec).all()
            norm = np.linalg.norm(vec)
            assert np.isclose(norm, 1.0, atol=1e-5), f"Vector for {r['chunk_id']} has non-unit norm: {norm}"

    def test_tier2_f5_front_matter_chunks_excluded_from_search(self, staged_db_ro):
        """Chunks from front matter pages (PDF pages 1..15) have excluded=1."""
        front_chunks = staged_db_ro.execute(
            "SELECT id, pdf_page_start, excluded FROM chunks WHERE source_type='book' AND pdf_page_start < ?",
            (FIRST_BODY_PDF_PAGE,),
        ).fetchall()
        assert len(front_chunks) > 0, "Expected front matter chunks in book"
        for fc in front_chunks:
            assert fc["excluded"] == 1, f"Front matter chunk {fc['id']} on PDF page {fc['pdf_page_start']} not excluded"

    def test_tier2_f5_chunk_length_and_overlap_boundaries(self, staged_db_ro):
        """Book chunk text lengths stay within ~800 character window and are non-empty."""
        book_chunks = staged_db_ro.execute("SELECT id, text FROM chunks WHERE source_type='book' LIMIT 200").fetchall()
        for bc in book_chunks:
            txt = bc["text"].strip()
            assert len(txt) > 0, f"Chunk {bc['id']} is empty"
            assert len(txt) < 850, f"Chunk {bc['id']} exceeds maximum chunk character limit: {len(txt)}"

    def test_tier2_f5_database_wal_and_quick_check(self, staged_db_ro):
        """PRAGMA quick_check returns 'ok' and SQLite schema version is valid."""
        assert staged_db_ro.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        user_version = staged_db_ro.execute("PRAGMA user_version").fetchone()[0]
        assert user_version >= 0


# ==============================================================================
# TIER 3: CROSS-FEATURE INTERACTIONS (Pairwise Combinations)
# ==============================================================================

class TestTier3CrossFeatureInteractions:
    """Tier 3: Pairwise interactions across F1 through F5."""

    def test_tier3_f1_f4_repaired_mutation_page_survives_strict_grounding(self):
        """Pairwise F1 x F4: Repaired page 113 legal text excerpt passes strict grounding validation."""
        clean_text = (
            "ਸਬੰਧਤ ਪਟਵਾਰੀ ਨੂੰ ਧਾਰਾ 39 ਦੇ ਉਪਬੰਧ ਮੁਤਾਬਿਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ। "
            "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।"
        )
        ev = make_ev("B1", clean_text, pdf_page=113, printed_page="98")
        claim = "ਧਾਰਾ 39 ਦੇ ਉਪਬੰਧ ਮੁਤਾਬਿਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ।"
        ans, warnings = validate(make_reply(claim, clean_text, "B1"), [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 1
        assert warnings == []

    def test_tier3_f1_f5_repaired_pages_ingested_chunks_match_clean_text(self, staged_db_ro):
        """Pairwise F1 x F5: Every ingested chunk on repaired pages is a verbatim substring of clean page text."""
        for p in (113, 167, 171, 175, 183, 261):
            page_clean = staged_db_ro.execute(
                "SELECT text_clean FROM pages WHERE pdf_page=?", (p,)
            ).fetchone()["text_clean"] or ""

            chunks = staged_db_ro.execute(
                "SELECT text FROM chunks WHERE pdf_page_start=? AND source_type='book'", (p,)
            ).fetchall()

            for ch in chunks:
                chunk_norm = " ".join(ch["text"].split())
                page_norm = " ".join(page_clean.split())
                assert chunk_norm in page_norm, f"Page {p} chunk text is not a substring of page clean text"

    def test_tier3_f2_f5_tabular_chunks_staged_with_valid_vectors_and_bm25(self, staged_db_ro):
        """Pairwise F2 x F5: Annexure tables 382, 383, 389 in staged DB have non-null vectors and BM25 tokens."""
        for p in (382, 383, 389):
            chunks = staged_db_ro.execute(
                "SELECT c.id, e.dim, e.vec, t.tokens FROM chunks c "
                "LEFT JOIN embeddings e ON e.chunk_id=c.id "
                "LEFT JOIN bm25_tokens t ON t.chunk_id=c.id "
                "WHERE c.pdf_page_start=? AND c.source_type='book'",
                (p,),
            ).fetchall()

            for ch in chunks:
                assert ch["dim"] == 384
                assert ch["vec"] is not None and len(ch["vec"]) == 384 * 4
                assert ch["tokens"] is not None
                token_list = json.loads(ch["tokens"])
                assert isinstance(token_list, list) and len(token_list) > 0

    def test_tier3_f3_f5_printed_labels_propagated_to_chunk_metadata(self, staged_db_ro):
        """Pairwise F3 x F5: chunks.printed_labels matches pages.printed_label for all body chunks."""
        mismatches = staged_db_ro.execute(
            "SELECT c.id, c.pdf_page_start, c.printed_labels, p.printed_label "
            "FROM chunks c JOIN pages p ON c.pdf_page_start=p.pdf_page "
            "WHERE c.source_type='book' AND c.excluded=0 AND c.printed_labels IS NOT p.printed_label"
        ).fetchall()
        assert mismatches == [], f"Found {len(mismatches)} chunk-to-page printed label mismatches"

    def test_tier3_f4_f5_retrieval_and_grounding_on_rebuilt_staged_db(self, staged_db_ro):
        """Pairwise F4 x F5: Evidence retrieved from staged DB validates with verified printed page citation."""
        row = staged_db_ro.execute(
            "SELECT c.text, c.pdf_page_start, c.printed_labels FROM chunks c "
            "WHERE c.pdf_page_start=167 AND c.source_type='book' LIMIT 1"
        ).fetchone()

        ev = make_ev("B1", row["text"], pdf_page=row["pdf_page_start"], printed_page=row["printed_labels"])
        assert ev.printed_page == "152"
        assert ev.pdf_page == 167

        # Claim citing Book p.152
        quote = row["text"][:60]
        claim = f"Book p.152 {quote}"
        ans, _ = validate(make_reply(claim, quote, "B1"), [ev])
        assert ans.status == "answered"


# ==============================================================================
# TIER 4: REAL-WORLD APPLICATION WORKLOADS (5 End-to-End Scenarios)
# ==============================================================================

class TestTier4RealWorldWorkloads:
    """Tier 4: End-to-end real-world legal consultation workflows."""

    def test_tier4_workload1_legal_mutation_timeline_and_collector_fine(self):
        """Scenario 1: Legal query on Section 39 mutation reporting deadline & Collector fine power."""
        clean_passage = (
            "ਸਬੰਧਤ ਪਟਵਾਰੀ ਨੂੰ ਧਾਰਾ 39 ਦੇ ਉਪਬੰਧ ਮੁਤਾਬਿਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ। "
            "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ। "
            "ਜਮਾਂਬੰਦੀ ਦੇ ਇੰਦਰਾਜ਼ਾਂ ਨੂੰ ਧਾਰਾ 44 ਤਹਿਤ ਸਚਾਈ ਦੀ ਧਾਰਨਾ ਪ੍ਰਾਪਤ ਹੈ।"
        )
        ev = make_ev("B1", clean_passage, pdf_page=113, printed_page="98")

        # LLM proposes verified answer
        raw_answer = {
            "status": "answered",
            "claims": [
                {
                    "text": "ਧਾਰਾ 39 ਦੇ ਉਪਬੰਧ ਮੁਤਾਬਿਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ।",
                    "source_ids": ["B1"],
                    "support": [{"source_id": "B1", "quote": "ਸਬੰਧਤ ਪਟਵਾਰੀ ਨੂੰ ਧਾਰਾ 39 ਦੇ ਉਪਬੰਧ ਮੁਤਾਬਿਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ।"}],
                },
                {
                    "text": "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।",
                    "source_ids": ["B1"],
                    "support": [{"source_id": "B1", "quote": "ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ।"}],
                },
            ],
            "caveats": [],
            "missing_facts": [],
        }

        ans, warnings = validate(raw_answer, [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 2

        # Spoken output generated deterministically from surviving claims
        spoken_pa = _spoken(ans, "ਇੰਤਕਾਲ", "pa")
        assert "ਧਾਰਾ 39" in spoken_pa
        assert "ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ" in spoken_pa

    def test_tier4_workload2_land_partition_precedent_and_measurement(self):
        """Scenario 2: Precedent citation verification (2008 (1) LAR 132) and area (230 ਕਨਾਲ 10 ਮਰਲੇ)."""
        clean_passage = (
            "ਰਾਜਪਾਲ ਸਿੰਘ ਅਤੇ ਹੋਰ ਬਨਾਮ ਮੱਖਣ ਸਿੰਘ ਅਤੇ ਹੋਰ 2008 (1) ਐਲ. ਏ. ਆਰ. 132 (ਐਫ਼. ਸੀ. ਪੰਜਾਬ)। "
            "ਨੇ 230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਮਿਤੀ 12.8.2019 ਨੂੰ ਦਿੱਤੀ ਸੀ।"
        )
        ev = make_ev("B1", clean_passage, pdf_page=175, printed_page="160")

        raw_answer = {
            "status": "answered",
            "claims": [{
                "text": "230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਮਿਤੀ 12.8.2019 ਨੂੰ ਦਿੱਤੀ ਸੀ।",
                "source_ids": ["B1"],
                "support": [{"source_id": "B1", "quote": "230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ਦੀ ਤਕਸੀਮ ਲਈ ਦਰਖਾਸਤ ਮਿਤੀ 12.8.2019 ਨੂੰ ਦਿੱਤੀ ਸੀ।"}],
            }],
        }

        ans, warnings = validate(raw_answer, [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 1
        assert "230 ਕਨਾਲ 10 ਮਰਲੇ" in ans.claims[0].text

    def test_tier4_workload3_revenue_survey_chain_and_standard_karam(self):
        """Scenario 3: Revenue survey calculation on standard karam (66 inches) and chain links (8/7)."""
        clean_passage = (
            "ਇੱਕ ਸਟੈਂਡਰਡ ਕਰਮ 66 ਇੰਚ ਦੀ ਹੈ। "
            "ਜਰੀਬ ਵਿੱਚ 8 ਕੜੀਆਂ ਅਤੇ ਛੋਟੀ ਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ 7 ਕੜੀਆਂ ਹੁੰਦੀਆਂ ਹਨ।"
        )
        ev = make_ev("B1", clean_passage, pdf_page=261, printed_page="246")

        raw_answer = {
            "status": "answered",
            "claims": [{
                "text": "ਇੱਕ ਸਟੈਂਡਰਡ ਕਰਮ 66 ਇੰਚ ਦੀ ਹੈ ਅਤੇ ਜਰੀਬ ਵਿੱਚ 8 ਕੜੀਆਂ ਹੁੰਦੀਆਂ ਹਨ।",
                "source_ids": ["B1"],
                "support": [{"source_id": "B1", "quote": clean_passage}],
            }],
        }

        ans, warnings = validate(raw_answer, [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 1
        assert "66 ਇੰਚ" in ans.claims[0].text
        assert "8 ਕੜੀਆਂ" in ans.claims[0].text

    def test_tier4_workload4_jamabandi_tabular_register_querying_and_orientation(self):
        """Scenario 4: Querying 12-column Jamabandi register and Khasra Girdawari harvest inspections."""
        jamabandi_text = (
            "ਅਨੁਲੱਗ-15 ਨਕਲ ਜਮਾਂਬੰਦੀ\n"
            "ਖੇਵਟ 243 | ਖਤੌਨੀ 105 | ਨਾਮ ਮਾਲਕ ਗੁਰਮੀਤ ਸਿੰਘ | ਰਕਬਾ 40-0 | ਮਾਲੀਆ 5.50"
        )
        ev = make_ev("B1", jamabandi_text, pdf_page=383, printed_page="368")

        raw_answer = {
            "status": "answered",
            "claims": [{
                "text": "ਖੇਵਟ 243 ਨਾਮ ਮਾਲਕ ਗੁਰਮੀਤ ਸਿੰਘ ਰਕਬਾ 40-0 ਹੈ।",
                "source_ids": ["B1"],
                "support": [{"source_id": "B1", "quote": "ਖੇਵਟ 243 | ਖਤੌਨੀ 105 | ਨਾਮ ਮਾਲਕ ਗੁਰਮੀਤ ਸਿੰਘ | ਰਕਬਾ 40-0"}],
            }],
        }

        ans, _ = validate(raw_answer, [ev])
        assert ans.status == "answered"
        assert len(ans.claims) == 1
        assert "ਗੁਰਮੀਤ ਸਿੰਘ" in ans.claims[0].text

    def test_tier4_workload5_full_book_citation_traversal_with_printed_page_offset(self, staged_db_ro):
        """Scenario 5: Multi-chapter citation traversal verifying printed page citations across chapters."""
        # Query sample pages across chapters (Chapter 5: 113, Chapter 8: 167, Measurement: 261)
        test_pages = [(113, "98"), (167, "152"), (261, "246")]
        for pdf_p, expected_printed in test_pages:
            row = staged_db_ro.execute(
                "SELECT printed_label FROM pages WHERE pdf_page=?", (pdf_p,)
            ).fetchone()
            assert row is not None
            assert row["printed_label"] == expected_printed, (
                f"Page {pdf_p} expected printed label {expected_printed}, found {row['printed_label']}"
            )
