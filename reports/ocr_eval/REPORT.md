# OCR comparison: Bhumbak book, 8-page sample (interim)

Source: `Punjabi book .pdf`, SHA-256 `2bba1b70…72980` (matches audit). Production DB untouched; backup at `reports/ocr_eval/jarvis.db.preeval-backup` (sha256 identical to `data/jarvis.db`).

Sample: `reports/ocr_eval/sample/sample_8pages.pdf`; mapping in `page_map.json`. Sample index 1..8 = original PDF pages 167, 170, 183, 184, 346, 368, 382, 383.

## Engines compared

| ID | Engine | Model | Notes |
|---|---|---|---|
| A | Jarvis existing | tesseract-5 pan+eng per-line (production) | Same 300 DPI gray render as sample (image hash matches). |
| B | OCRmyPDF `-l pan+eng --rotate-pages --deskew` | legacy `pan` from tesseract-lang 4.1.0 | Sidecar text. |
| C | OCRmyPDF `-l pan+eng --rotate-pages --deskew` | `tessdata_best` pan+eng+osd | Configs copied from the installed tessdata. |
| D | Tesseract direct, `--oem 1 --psm 6` | `tessdata_best` pan+eng | Pages 382 and 383 rotated 270° first. |

Note: the installed `pan.traineddata` is the legacy model, so the existing Jarvis OCR and engine B use legacy weights. Engine C/D is the first `tessdata_best` test.

## Rotation (measured)

Tessdata_best mean word confidence at 0/90/180/270°:

- 382: 63 / 60 / 63 / **83** (26 words at 270; table largely empty)
- 383: 27 / 44 / 24 / **83** (74 words at 270; 16 words at 0)
- 368: **87** at 0°; 346: **86** at 0° (upright, no rotation)

OSD (`--psm 0`) said 0° for 167–368, 90° with low confidence (1.57) for 382, and failed for 383. OSD is not reliable on these pages. The scans show 382 and 383 as sideways tables; the 270° result is the one the OCR confirms.

## Key findings on the audit's named problems

| Item | A: Jarvis existing | B: OCRmyPDF legacy | C: OCRmyPDF best | D: Tesseract best psm6 |
|---|---|---|---|---|
| p.167 notification date `1.12.2008` | **absent** | correct | correct | **`112.2008`** (wrong) |
| p.167 NRI paragraph (`ਪ੍ਰਵਾਸੀ ਭਾਰਤੀ`) | **absent / garbled** | present | present | present |
| p.167 officer line (`ਕਰਨ ਦੇ ਅਧਿਕਾਰ ਕੇਵਲ ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ ਨੂੰ ਨੋਟੀਫਿਕੇਸ਼ਨ ਮਿਤੀ`) | absent | **absent** | **absent** | **absent** |
| p.183 section `150` (`ਧਾਰਾ 150 ਤਹਿਤ`) | **absent** | present | present | present |
| p.183 `ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾ` refusal/eviction sentence | partial | present | present | present |
| p.170 `ਅਨੁਲੱਗ` (annex refs) | present | present | present | present |

Checked against the scan (page 167 and page 183 viewed at 300 DPI): the date reads `1.12.2008`; `ਧਾਰਾ 150 ਤਹਿਤ` is printed on page 183 and the existing Jarvis text does not contain it. The officer line on 167 is in the scan and is missing from all four outputs.

## Measured errors (what is and is not measured)

- Measured: presence/absence of specific tokens, words per page, and mean word confidence (for rotation only).
- Not yet measured: character or word error rate. That needs a verified ground-truth transcription of each page, which has not been made. I have not made one, so no CER/WER figures are reported.
- Not measured for pages 184, 346, 368, 382, 383 beyond the counts above; no visual line-by-line comparison has been done.

## Unresolved

1. The officer line on page 167 is lost in every engine. Any replacement text will still be wrong there unless a person transcribes it from the scan.
2. Engine D (direct `tessdata_best`) has worse number handling on 167 (`112.2008`). Engines B and C are better on numbers here.
3. Engine A (existing) loses section 150 and the date. This confirms the audit.
4. Pages 382/383 (and 389) still need structure-preserving table extraction; plain OCR text does not keep row/column association. Not done yet.

## Not done (per the task)

- No method selected yet (step 7 requires inspection of more pages first).
- No corrected text, staged database, chunk/embedding/BM25 rebuild (steps 7–8). Nothing activated.
- No reconstruction of missing legal text from model knowledge.

## Files

- `candidates/<engine>/page_NNNN.txt`: four candidate texts per page.
- `candidates/…` built by `build_candidates.py`; rotation probe in `rotation_probe.py`; sample built by `make_sample.py`.
- `render/page_NNNN.png`: 300 DPI grayscale renders.
- `ocrmypdf_legacy/`, `ocrmypdf_best/`: OCRmyPDF outputs and logs.
