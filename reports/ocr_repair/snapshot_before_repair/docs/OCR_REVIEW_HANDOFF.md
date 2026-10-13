# OCR review and corrected-index handoff

## Ownership

Claude Code handles extraction experiments, corrected page text and a staged database. These application changes handle review provenance, citation display and import consistency checks. Do not overwrite either agent's changes. Keep the original scanned PDF unchanged.

## What the application now shows

- `extracted`: text exists, but no matching scan review has been recorded.
- `needs_review`: extraction was flagged, a prior review is stale, or a retrieved chunk no longer matches the page text.
- `scan_verified`: an explicit reviewer record matches both the page text SHA-256 and source image SHA-256. This verifies transcription only, not legal accuracy or applicability.

Existing `quality=ok` never becomes `scan_verified` automatically. Pages without review records remain unverified. Both primary evidence and adjacent book context carry these states. The model prompt and answer warning identify unverified book OCR and call for scan/official-source checks for fees, deadlines and officer powers.

Each book citation has a **Compare scan** control. The evidence modal displays the original image and the exact excerpt used in that answer. Earlier answers retain their own excerpts and page identities. The library counts pages verified against scans separately from searchable pages.

Original-page display uses `JARVIS_BOOK_PDF` when configured; otherwise it looks for `Punjabi book .pdf` in the project folder. It serves images only if the PDF SHA-256 matches the indexed book document. A new OCRmyPDF output should not replace the original scan used for comparison. Rendering uses PyMuPDF, or installed Poppler as a fallback.

## Import checks for Claude Code

Use the project's Python environment:

```bash
python scripts/check_ocr_import.py \
  --db reports/ocr_repair/jarvis.staged.db \
  --baseline-db data/jarvis.db \
  --expected-pages reports/ocr_repair/expected_pages.json \
  --out reports/ocr_repair/import_check.json
```

The script is read-only for both databases. Exit code 1 means the index/page checks failed. The paths above are intended output paths for Claude, not files already created by this change.

`expected_pages.json` is a list binding each intended correction to a source page and exact final text:

```json
[
  {
    "doc_id": 1,
    "pdf_page": 167,
    "printed_page": "152",
    "text_sha256": "SHA256_OF_EXACT_CORRECTED_TEXT_CLEAN"
  }
]
```

Resolve the actual book document ID from the staged database; do not assume it is 1. Compute hashes from the exact UTF-8 page text stored in `pages.text_clean`.

The checker verifies SQLite/foreign-key integrity, vector presence/dimensions/values, token consistency, book chunk-to-page association, printed labels and expected corrected text hashes. With a baseline, it rejects changed chunk text that reuses the same stored vector under the same ID. It cannot prove that an arbitrary nonidentical vector was correctly generated: rebuild embeddings from corrected text and rerun retrieval checks.

A passing import check does **not** certify OCR accuracy. It reports verified/unverified page counts separately. Visually compare corrections against the scans and rerun the existing `tests/gold.csv` and `tests/heldout.csv` retrieval checks on the staged database. Under the current language policy, three Hindi queries intentionally skip book search; assess them separately through law evidence.

## Recording a real scan review

After comparing the complete corrected page with its scan, use `ocr_review.record_review()` on the staged database. Supply the actual document ID, PDF page, status `scan_verified`, reviewer identity, and the exact text/image hashes that were reviewed. A missing or mismatched hash is rejected. Use `needs_review` for an explicit unresolved review. Never mark an OCR success or an uninspected page as verified.

The records live in `page_reviews`; the application creates the table when opening a writable legacy database. Read-only legacy databases are supported without migration. Changed text/images invalidate existing reviews, and stale retrieved chunks cannot inherit a corrected page's verification. Preserve review records only when these bindings remain valid during re-ingestion.

## Verification for this change

Tests cover expiry on text/image changes, stale chunks, false verification from extraction success, missing vectors, stale tokens, source-page mismatch, expected correction hashes, baseline vector reuse, actual scan rendering and wrong-PDF rejection. The JavaScript test checks that both citation and scan controls in an older answer open that answer's evidence after a newer answer.

Browser visual verification was unavailable: the browser security policy rejected the local-file preview, and no live server was available to this session. API image rendering and DOM-adapter click behavior were tested. `reports/ocr_audit/ui_preview.html` is a local preview using the production rendering code with fixture responses; it is not a live synthesis or server test.

Restart Jarvis after applying these application changes or activating corrected data; its retrieval pools are held in memory. OCR correction and legal release auditing remain separate work.
