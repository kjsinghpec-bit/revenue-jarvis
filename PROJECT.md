# Project: Revenue-Jarvis OCR Pipeline Hardening & Repair

## Architecture
- **OCR Engine & Review Pipeline**: `src/revenue_jarvis/ocr_review.py`, `src/revenue_jarvis/ocr.py`, `reports/ocr_repair/`
- **Book Ingestion & Page Indexing**: `src/revenue_jarvis/ingest/book.py`, `src/revenue_jarvis/db.py`, `src/revenue_jarvis/text.py`
- **Dense & Lexical Retrieval / Indexing**: `src/revenue_jarvis/index.py`, `src/revenue_jarvis/retrieve.py`, `scripts/repair_law_index.py` (offline `CachedE5`)
- **Answer Grounding & Verification Safeguards**: `src/revenue_jarvis/grounding.py`, `src/revenue_jarvis/answer.py`
- **Audit & Staging Verification**: `src/revenue_jarvis/ocr_review.py` (`check_import`), `reports/ocr_repair/build_staged.py`
- **Test Infrastructure**: `tests/` (156 baseline tests; offline in-memory fixtures)

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | R1: Blocking OCR Pages Repair | Repair confirmed defective pages (113, 175, 261, 167, 171, 183) matching readable original scan without OCR artifacts | M1 | ORIGINAL_REQUEST §R1 |
| F2 | R2: Orientation & Tabular Extraction | Automatic 90° CW/CCW orientation correction and multi-column tabular extraction for landscape annexures / Jamabandi templates (382, 383, 389) | M2 | ORIGINAL_REQUEST §R2 |
| F3 | R3: Printed Page Label Coverage | Improve page header detection in `book.py` to achieve >95% coverage across all 374 body pages (<15 unmapped, 0 false mismatches, offset PDF-15) | M3 | ORIGINAL_REQUEST §R3 |
| F4 | R4: Regression & Grounding Safeguards | Regression test suite ensuring corrupt OCR claims are rejected and repaired claims pass validation | M4 | ORIGINAL_REQUEST §R4 |
| F5 | R5: Staged DB Rebuild & Law Corpus Preservation | Re-ingest repaired pages, generate vectors/tokens into staged DB, pass `check_import`, preserve 27 law docs & 2,213 chunks 100% byte-identical | M5 | ORIGINAL_REQUEST §R5 |
| F6 | E2E Testing & Adversarial Hardening | Comprehensive multi-tier test suite (Tiers 1-4) publishing `TEST_READY.md`, followed by 100% pass and Tier 5 adversarial hardening | E2E / M_FINAL | ORIGINAL_REQUEST Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Blocking OCR Pages Repair | Correct text transcriptions and clean OCR representations for pages 113, 175, 261, 167, 171, 183, 179 | none | IN_PROGRESS (worker_m1_1: 408416c7) |
| M2 | Orientation & Tabular Extraction | Rotation handling (90° CW/CCW) and structured table extraction for pages 382, 383, 389 | none | PLANNED |
| M3 | Printed Page Label Coverage | Header detection algorithm in `src/revenue_jarvis/ingest/book.py` achieving >95% body page coverage | none | PLANNED |
| M4 | Regression & Grounding Safeguards | Add `tests/test_ocr_repairs_grounding.py` verifying claim rejection of corrupted text and acceptance of clean text | M1 | PLANNED |
| M5 | Staged DB Rebuild & Corpus Preservation | Re-ingest all repaired pages into `reports/ocr_repair/jarvis.staged.db`, re-embed with `CachedE5`, record `needs_review`, pass `check_import` | M1, M2, M3 | PLANNED |
| M_FINAL | 100% E2E Pass & Adversarial Hardening | Pass 100% of E2E tests across Tiers 1-4, then run Tier 5 adversarial coverage hardening | M4, M5, E2E | PLANNED (TEST_READY.md published) |

## Interface Contracts
### OCR Page JSON Contract (`reports/ocr_repair/ocr_selected/page_{0001..0389}.json`)
- Must maintain schema: `{"pdf_page": int, "n_lines": int, "failed_lines": int, "engine": str, "image_sha256": str, "lines": [{"box": [y0,x0,y1,x1], "text": str, ...}], "text_raw": str, "text_clean": str}`
- Clean text must contain verbatim legal terms matching readable original scan.

### Table Extraction Contract (Pages 382, 383, 389)
- Oriented text extraction preserving column structure. No horizontal column interleaving or non-semantic noise characters.

### Ingestion & Page Label Contract (`src/revenue_jarvis/ingest/book.py:detect_printed_label`)
- `detect_printed_label(lines: list[str], pdf_page: int) -> tuple[str | None, str]`
- Returns `(str(expected), "ocr_verified")` if verified from scanned text header/footer where `expected == pdf_page - 15`; otherwise `(None, "unknown")`.
- Must achieve >95% coverage across all 374 body pages (fewer than 15 unmapped body pages) with 0 false mismatches.

### Grounding & Answer Validation Contract (`src/revenue_jarvis/answer.py:validate`)
- Rejects unsupported fees, penalty multipliers, officer power mismatches, and statutory deadlines from corrupted text.
- Accepts valid claims supported by repaired clean text.

### Database Staging & Integrity Contract (`src/revenue_jarvis/ocr_review.py:check_import`)
- `check_import(con_staged, baseline=con_baseline) -> {"passed": True, "errors": []}`
- 0 SQLite integrity errors, 0 foreign key violations, 0 orphan records in embeddings or bm25_tokens.
- 27 law documents and 2,213 law chunks remain 100% byte-identical to baseline production backup.
- All AI-reviewed pages recorded with `status: 'needs_review'`; 0 pages marked `scan_verified`.

## Code Layout
- `src/revenue_jarvis/ingest/book.py` — Ingestion logic, printed page label detection (`detect_printed_label`)
- `src/revenue_jarvis/ocr_review.py` — Review tracking, import gate verification (`check_import`)
- `src/revenue_jarvis/grounding.py` — Fact extraction, authority frames, quote support validation
- `src/revenue_jarvis/answer.py` — Claim validation engine (`validate`)
- `reports/ocr_repair/ocr_selected/` — Authoritative repaired OCR JSON outputs for pages 1–389
- `reports/ocr_repair/groundtruth/` — Ground truth transcriptions verified against scan
- `reports/ocr_repair/jarvis.staged.db` — Staged database rebuilt from production backup
- `reports/ocr_repair/backup/jarvis.production-20261013-141120.db` — Baseline production backup (read-only)
- `tests/test_ocr_repairs_grounding.py` — Dedicated regression test suite for R4
- `tests/test_e2e_ocr_pipeline.py` — Comprehensive E2E test suite for pipeline acceptance
