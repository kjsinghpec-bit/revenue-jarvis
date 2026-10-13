# Notes for Claude's ongoing OCR repair

Read-only review of `reports/ocr_repair/build_staged.py`, `run_engine.py` and preservation metadata. At inspection, 51/389 selected-output page JSON files existed. No OCR scripts, outputs or staged database were edited by Codex.

## Before building or activating

- The builder currently accepts an incomplete OCR directory. Confirm all 389 original page identities are present and valid before calling it. Count and verify page identities, not just filenames.
- Use the current application code and test suite, not the `snapshot_before_repair` code. The current suite has **156 passing tests**; the earlier snapshot's 136 count predates grounding fixes.
- Read the updated `docs/OCR_REVIEW_HANDOFF.md`. With `--baseline-db`, the import gate now rejects missing original book page records, loss of previously searchable book pages, and any change to existing law documents/chunks/vectors/tokens. Baseline checks were exercised on production versus the SQLite backup and pass.
- Keep AI-reviewed text marked `needs_review`; do not use CER against AI transcription as independent human accuracy or legal-answer accuracy.
- Inspect segmentation on untuned chapters. The 120-pixel choice was selected on the same four pages used for the pilot comparison.
- Rotation confidence is not proof of correct orientation or table cell association. Visually review rotated and low-confidence pages.
- `orientation()` currently uses a shared temporary probe filename and has no subprocess timeout/return-code check. Avoid simultaneous runs that share that file; handle probe failures explicitly before interpreting scores.
- Resolve the missing officer passage from the readable original scan before treating page 167 as repaired. Do not choose a candidate solely because a date or section token is present.

The gate additions are in `src/revenue_jarvis/ocr_review.py`; extraction ownership remains with Claude. Keep the existing original-scan source hash for citation images. The database remains unverified until the actual staged checks and page comparisons are completed.
