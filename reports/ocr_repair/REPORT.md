# Bhumbak book OCR repair: final report

Date: 13 October 2026. Source PDF SHA-256 `2bba1b70125a07d04efbc5c9f0dc06ad0059367e929fc2ffa9555c2a95e72980` (unchanged).

## Status

- Extraction: complete for all 389 PDF pages (`ocr_selected/`).
- Staged database: built and checked (`jarvis.staged.db`).
- **Activated**: `data/jarvis.db` now holds the repaired book text. Activation manifest: `activation_manifest.json`.
- Whole-book accuracy is **not** measured. Only the four partition pages were compared against scans.

## Selected extraction method

Per-line Tesseract 5.5 with `tessdata_best` `pan+eng`, with two changes:

1. Lines are split at 120 px instead of 170 px. Tall bands were merging two legal lines (for example, the NRI paragraph on PDF 167).
2. Each page is checked at 0/90/180/270° and rotated only when a turned reading beats upright by more than 5 mean-confidence points. 19 pages were rotated 270°.

Measured on the four partition pages (AI transcriptions of the scans, not human-verified), pooled character error rate:

| Pipeline | CER |
|---|---|
| Existing Jarvis OCR (legacy model, 170 px split) | 0.124 |
| OCRmyPDF, legacy model | 0.265 |
| OCRmyPDF, tessdata_best | 0.255 |
| tessdata_best, 170 px split | 0.118 |
| legacy model, 120 px split | 0.041 |
| **tessdata_best, 120 px split (selected)** | **0.034** |

Per-page CER for the selected pipeline: 167 = 0.044, 170 = 0.021, 183 = 0.032, 184 = 0.038.

## Page processing and review status

| Group | Pages | Status |
|---|---|---|
| Processed (all 389 pages, rendered at 300 DPI) | 1–389 | OCR complete; 0 failed lines |
| Visually compared with the scan | 167, 170, 183, 184 | AI comparison; recorded as `needs_review`, not human-reviewed |
| Visually checked, unreadable scanned map | 321, 334 | recorded as `needs_review` |
| Visually checked (sideways tables, pilot) | 382, 383 | orientation confirmed (270°); cell association **not** verified |
| Visually checked (bilingual glossary, pilot) | 346, 368 | upright; column association **not** verified |
| Front matter (1–15) | 1–15 | indexed as excluded, as before |
| Blank | 30 | empty, as the audit found |
| All other pages | the remaining ~370 | OCR output only; **unverified** |

No page is `scan_verified`. Page status is `needs_review` for the six reviewed pages and `extracted` otherwise.

## Corrections confirmed against the scan (partition pages)

- PDF 167: notification date reads `1.12.2008`; the district revenue officer sentence (`ਕਰਨ ਦੇ ਅਧਿਕਾਰ ਕੇਵਲ ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ ਨੂੰ ਨੋਟੀਫਿਕੇਸ਼ਨ ਮਿਤੀ`) is present.
- PDF 183: section `150` present; printed page `168` (label confirmed from the page text).

Remaining known error: the 167 date and officer sentence still contain a few wrong words in some outputs. Use the scan.

## Import check (`import_check.json`)

- `check_ocr_import.py` passed with 0 errors.
- SQLite integrity ok; 2,835 searchable book chunks; no orphan or missing vectors or tokens; expected-page hashes match.
- Scan-verified book pages: 0. Unverified: 373 searchable pages.
- Front matter (1–15) was removed from the expected-page manifest, because it is intentionally not searchable. The first check run failed only on those pages.

## Tests

- `pytest`: 156 passed, 0 failed (the earlier count was 136; the other agent added tests).

## Retrieval (`retrieval_comparison.json`)

Same encoder (cached `multilingual-e5-small`), same settings, run on copies of both databases.

| Benchmark | Baseline | Staged |
|---|---|---|
| gold, non-Hindi | 18/18 | 18/18 |
| heldout, non-Hindi | 9/9 | 9/9 |
| Hindi (book search skipped by policy) | 0/3 | 0/3 |
| total gold + heldout | 27/27 non-Hindi | 27/27 non-Hindi |

No per-question changes. Hindi queries are answered from law sources by policy and were not counted.

Partition evidence check (`partition_evidence.json`): the officer sentence appears in retrieved book evidence for English and Gurmukhi questions. Section 150 appears for both. The date `1.12.2008` appears for the Gurmukhi question but not for the English question.

## Live application checks

- `/api/status`: 389 book pages, 373 indexed.
- `/api/page/167/text`: corrected text served; `needs_review`.
- `/api/page/167.png`: original scan served, HTTP 200.
- Partition question (English) "Who decides partition cases of non-resident Indian petitioners?": evidence pages 167, 170, 182, 168, 184; **answer withheld** by grounding validators ("Claim cites the wrong section/rule/paragraph").
- Partition question (Gurmukhi) "which section applies for removing illegal occupation of shared land": evidence pages 164, 183, 177, 246; **answer withheld** ("Unsupported numeric amount/date/unit: 1.5E+2"). This appears to be a number-format issue in the validator (150 read as 1.5E+2). Not investigated further.
- Citation display and history were not exercised beyond these two requests (history rows added to `qa_log`).

Retrieval was correct in both live requests; the answers were withheld by the grounding checks, not by OCR.

## Activation and rollback

- Activated by SQLite backup API (staged to `data/jarvis.db`). No process held the file at activation.
- Rollback copy: `backup/jarvis.rollback-before-activation-20261013-193309.db` (SHA-256 `ead68d0c…`).
- Rollback: stop Jarvis, copy the rollback file back via the backup API, restart with `Start Jarvis.command`. Command is in `activation_manifest.json`.
- Jarvis was restarted with `Start Jarvis.command` (background; log `jarvis_server.log`). It listens on 127.0.0.1:8765.

## Unresolved

1. Whole-book accuracy unknown. 373 pages are unverified; the 19 rotated pages were not visually checked (except 382 and 383).
2. Sideways tables (382, 383, 389) and bilingual glossaries (346, 368) are extracted as flat text. Row/column association is not verified.
3. Pages 321 and 334 are scanned maps; OCR cannot read them and both old and new text is junk. They are marked `needs_review`.
4. Gurmukhi answer withheld by a numeric validator (1.5E+2). Needs a fix in the grounding code, not in the OCR.
5. The English question's evidence did not include the 1.12.2008 date.
6. Claude synthesis quality was not measured on a representative set; only two requests were run and both were withheld.

## Files

- `ocr_selected/`: 389 page JSON records (`engine`, `split_px`, `rotation_deg`, `image_sha256`).
- `groundtruth/`: AI transcriptions of pages 167, 170, 183, 184 (not human-verified).
- `pilot_error_rates.json`, `segmentation_experiment.py`, `measure.py`: error measurements.
- `jarvis.staged.db`, `expected_pages.json`, `import_check.json`, `retrieval_comparison.json`, `partition_evidence.json`.
- `preservation.json`, `backup/`, `activation_manifest.json`.
