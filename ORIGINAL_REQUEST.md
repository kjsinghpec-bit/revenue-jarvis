# Original User Request

## Initial Request — 2026-10-13T14:32:24Z

Repair and harden the Revenue-Jarvis OCR pipeline, table extraction, and answer grounding based on independent audit findings. The project targets verified transcriptions for broken statutory clauses, robust landscape/annexure table handling, complete printed page label coverage, and automated regression safeguards.

Working directory: `/Users/karamjot/projects/revenue-jarvis`
Integrity mode: development

## Requirements

### R1. Targeted Repair of Confirmed Blocking OCR Pages
Correct text transcriptions and clean OCR representations for confirmed defective pages:
- Page 113: Section 39 mutation reporting deadline (3 months), Collector discretionary fine power (up to 5x fee), Section 44 presumption of truth.
- Page 175: Partition precedent citation (`2008 (1) L.A.R. 132`), land measurement (`230 ਕਨਾਲ 10 ਮਰਲੇ`), application filing date.
- Page 261: Standard Karam revenue unit (`66 ਇੰਚ`), survey chain link counts, and conversion series.
- Pages 167, 171, 183: Assistant Collector designation (`ਦਰਜਾ ਪਹਿਲਾ`), sanction clause (`ਇਸ ਨੂੰ ਮੰਜੂਰ`), and registration exemption (`ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ`).

### R2. Orientation Detection & Tabular Extraction for Annexures
Implement automatic orientation correction (handling 90° CW/CCW rotations) and structured multi-column tabular extraction for landscape annexures and Jamabandi templates (Pages 382, 383, 389), preventing horizontal column interleaving and non-semantic noise generation.

### R3. Complete Printed Page Label Coverage
Improve printed page header number detection in `src/revenue_jarvis/ingest/book.py` so that the 52 body pages currently recorded as `printed_label: null` are mapped accurately to their verified offset (`PDF page - 15`) without inferring unverified numbers.

### R4. Regression & Grounding Safeguard Verification
Add regression test suites ensuring that unsupported fees, penalty multipliers, officer powers, and statutory deadlines from corrupted text are rejected by answer grounding validation, and that newly repaired claims pass.

### R5. Staged Database Rebuild & Law Corpus Isolation
Re-ingest repaired pages, generate dense vectors and BM25 tokens into a staged database, pass all `check_import` gate verifications, and guarantee that the statutory law corpus (27 documents, 2,213 chunks) remains 100% byte-identical to the baseline.

## Verification Resources
- Audit report: `reports/independent_audit/REPORT.md`
- Original source document: `Punjabi book .pdf` (SHA-256: `2bba1b70125a07d04efbc5c9f0dc06ad0059367e929fc2ffa9555c2a95e72980`)
- Import gate script: `src/revenue_jarvis/ocr_review.py` (`check_import`)
- Baseline production backup: `reports/ocr_repair/backup/jarvis.production-20261013-141120.db`

## Acceptance Criteria

### Correctness & Data Quality
- [ ] `page_0113.json`, `page_0175.json`, `page_0261.json`, `page_0167.json`, and `page_0183.json` contain verified text matching the readable original scan without OCR noise artifacts.
- [ ] Pages 382, 383, and 389 extract correctly oriented text without generating non-semantic symbol strings or interleaving multi-column glossary cells.
- [ ] Printed page label detection achieves >95% coverage across all 374 body pages (fewer than 15 unmapped body pages) with zero false label mismatches.

### Corpus Preservation & Gates
- [ ] `check_import` passes on the resulting database with 0 integrity check errors, 0 foreign key violations, 0 orphan records in embeddings or bm25_tokens.
- [ ] All 27 statutory law documents and 2,213 law chunks remain byte-identical to the baseline production backup.
- [ ] Any AI-reviewed page text records `status: needs_review` in `page_reviews`; no automated or uninspected page is marked `scan_verified`.

### Test Suite
- [ ] All 156 existing test suite checks continue to pass.
- [ ] New unit and regression tests added covering the repaired clauses, table rotation, and grounding validator checks.
