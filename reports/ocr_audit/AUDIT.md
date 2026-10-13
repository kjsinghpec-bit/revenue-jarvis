# Bhumbak book OCR audit

13 October 2026. Source: `Punjabi book .pdf`, 389 pages. SHA-256 matches the original book document stored in Jarvis: `2bba1b70125a07d04efbc5c9f0dc06ad0059367e929fc2ffa9555c2a95e72980`.

## Result

The four partition pages inspected have material OCR errors despite the database's `ok` flags. The scans are readable enough to recover the affected passages. Search changes alone cannot repair this evidence.

Open `comparison.html` to see each original scan beside the text actually stored in the database. This audit visually inspected PDF pages 1, 30, 167, 170, 183, 184, 346, 368, 382, 383 and 389. It does not certify the remaining pages or estimate a whole-book accuracy percentage.

| PDF page | Printed page visible in scan | Confirmed problem |
| --- | --- | --- |
| 167 | 152 | The NRI paragraph loses the deciding-officer reference and the notification date `1.12.2008`; Punjabi officer wording is corrupted. |
| 170 | 155 | Application-document and respondent-copy lines contain Latin gibberish within Punjabi text. |
| 183 | 168 | Section `150` is missing from the final paragraph; the registration-exemption sentence and refusal grounds are damaged. |
| 184 | 169 | The remand paragraph and legal terminology contain recognition errors. |
| 30 | None | Visibly blank scan; empty OCR is expected. |
| 382 | 367 | Sideways table with real content; near-empty OCR is an extraction failure. |
| 383 | 368 | Sideways jamabandi example; the current line extraction loses table structure. |
| 389 | 374 | Another sideways table requiring rotation and structured extraction. |
| 346, 368 | 331, 353 | Bilingual glossary tables; row and column associations matter. These are dictionary material, not partition-procedure instructions. |

The references above describe what is printed in this book. They are not verification of current law, officer jurisdiction or notification applicability.

## Whole-book screening

All 389 OCR page records exist. Of 374 records classified as body pages, existing flags say 371 `ok`, one `partial`, and two `empty`. The page 30 blank and page 382 rotated table show why empty status alone cannot distinguish valid emptiness from missed content.

`full_book_screen.json` checks all body-page text for lines containing both Gurmukhi and Latin words of at least three letters. It flags 350 pages, including 133 with five or more such lines. These counts are **review candidates**, not proven-error counts: bilingual glossary entries and legitimate English words also trigger the heuristic.

The current quality logic marks a page `ok` if enough text exists and no attempted line returned empty. It does not measure word accuracy, whether line segmentation missed text, preservation of numbers/negation, or table layout. The visual audit disproves treating that flag as verified accuracy.

## OCR experiment

Rendered PDF page 167 at 300 DPI and tested:

- Tesseract `pan+eng`, full-page PSM 6.
- The same mode on a cropped text region.
- The existing per-line engine on the new rendering.

All three still lose or corrupt text. The fresh per-line run reports **31 lines and zero failed lines**, while the deciding-officer passage remains unreadable. Full-page mode drops several complete lines. Candidate text files are retained for inspection and have not replaced production evidence.

## Repair order

1. Transcribe and verify the partition chapter against scans, starting with the four confirmed failing pages. Preserve paragraph boundaries and exact section numbers, dates, negations and officer names. Keep before/after records and source image hashes.
2. Rebuild chunks, embeddings and BM25 tokens for corrected pages together; verify page labels and retrieval on both Punjabi and English questions. Use a staged database before activation.
3. Handle sideways annexures separately: rotate, retain row/column relationships, and flag uncertain cells. Do not convert a table into arbitrary prose.
4. Separate `extracted`, `needs_review` and `scan_verified` status. A successful OCR call is only extraction status. Numeric and authority claims need reliable text and applicable official support.
5. Audit frequent answer evidence plus a stratified sample across chapters; expand where errors cluster. A second OCR output can identify disagreement, but agreement alone is not proof of accuracy.

No production database or indexed text was changed during this inspection. The confirmed defective text is still present until repaired. This report establishes the problem and provides inspectable comparisons; it is not a completed book transcription or legal release certification.
