# Independent Audit of Revenue-Jarvis OCR Repair

**Date:** 13 October 2026  
**Auditor:** Independent Auditor Agent (Codex)  
**Target Repository:** `/Users/karamjot/projects/revenue-jarvis`  
**Mode:** Strictly Read-Only (no modifications to source code, OCR files, staged database, or production database; no activation performed)  
**Primary Evidence Inspected:** `Punjabi book .pdf` (SHA-256: `2bba1b70125a07d04efbc5c9f0dc06ad0059367e929fc2ffa9555c2a95e72980`), `reports/ocr_repair/ocr_selected/`, `reports/ocr_repair/jarvis.staged.db`, `reports/ocr_repair/backup/jarvis.production-20261013-141120.db`.

---

## 1. Executive Summary & Audit Scope

This independent audit evaluated the repaired OCR outputs produced by Claude (`reports/ocr_repair/ocr_selected/`) and the staged database (`reports/ocr_repair/jarvis.staged.db`).

### Key Findings
1. **Catalog Completeness (Task 1):** All 389 original PDF pages exist in `ocr_selected/` with matching internal page identities. There are no missing files, no orphaned records, and exactly one blank page (page 30, verified blank in scan).
2. **Key Target Recovery (Task 4):**
   - **Page 167:** The previously omitted DRO officer reference (`ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ`) and notification date (`1.12.2008`) were successfully restored to the text and indexed chunks. However, substantial surrounding text corruptions remain (`TI ਪਹਿਲਾ` for `ਦਰਜਾ ਪਹਿਲਾ`, `set ane` for `ਨਕਲਾਂ ਕਰਮਵਾਰ`, `ਫ਼ੈਸਲਾ ਜ਼ਿਲਾ doe` for `ਫ਼ੈਸਲਾ ਜ਼ਿਲ੍ਹਾ ਪੱਧਰ`).
   - **Page 183:** Section `150` for removing unauthorized possession from common land was successfully restored to the text and indexed chunks. Minor corruptions remain in adjacent clauses.
3. **Newly Discovered Blocking Problems:**
   - **Page 175 (Partition Case Citation & Land Measurement):** Catastrophic degradation across the middle and lower paragraphs. Case citation `ਰਾਜਪਾਲ ਸਿੰਘ ਅਤੇ ਹੋਰ ਬਨਾਮ ਮੱਖਣ ਸਿੰਘ... 2008 (1) ਐਲ. ਏ. ਆਰ. 132 (ਐਫ਼. ਸੀ. ਪੰਜਾਬ)` is reduced to garbled characters, land measurement `230 ਕਨਾਲ 10 ਮਰਲੇ` is corrupted to `੭30 ਕਲੀ 17 ਨ 9`, and filing dates are scrambled.
   - **Page 113 (Statutory Mutation Deadline & Collector Fine Power):** Statutory 3-month notice period under Section 39 and Collector's discretionary fine power (up to 5x mutation fee) are severely corrupted: `ਕਲੈਕਟਰ` is recognized as `ABC`, `ਫ਼ੀਸ` as `SIF`, `ਧਾਰਾ 39` as `35 © ਤਰਸ`, and Section 44 presumption of truth is garbled.
   - **Pages 382, 383, 389 (Sideways / Landscape Annexure Tables):** The per-line segmentation pipeline completely fails on rotated tables. Page 382 (Khasra table) contains strings of pure gibberish; Page 383 (12-column Jamabandi table) is inverted/rotated and completely lost; Page 389 (Khasra Girdawari register) is flattened into unsearchable noise.
   - **Page 261 (Land Measurement Chain & Unit Standards):** Critical measurement numbers are corrupted: standard karam `66 ਇੰਚ` is extracted as `cc ਇੰਜ`, and unit conversions are fragmented.
4. **Staged Database Integrity (Task 6):**
   - Claude's staged database passed all structural import checks (`check_import` passed).
   - Law corpus is 100% preserved (all 27 law documents and 2213 chunks are byte-identical to the baseline).
   - All 6 review records in `page_reviews` are appropriately designated `needs_review` (none falsely marked `scan_verified`).

---

## 2. Page Integrity Verification (Pages 1–389)

Every JSON file in `reports/ocr_repair/ocr_selected/page_{0001..0389}.json` was validated against its file identity and JSON structure:
- **Total files:** 389 / 389.
- **Identity matches:** 389 / 389 have `data['pdf_page'] == page_num`.
- **Empty pages:** Exactly 1 page (PDF page 30), which is visibly blank in the original scan.
- **Reported failed lines:** 0 across all 389 files.
- **Engine record:** `selected: tessdata_best per-line split120 retry probe` across all 389 files.
- **Printed page label extraction:** 52 body pages (out of 374 body pages, 13.9%) failed printed page label detection (`printed_label: null`, `label_source: unknown`) because the page header numbers were cut off or omitted by the vertical line-slicing window.

---

## 3. Visual Scan vs. Extracted Text Comparisons

A total of **27 individual pages** were visually audited directly against rendered scan images from `Punjabi book .pdf`:
- **Partition Chapter (13 pages):** PDF pages 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179.
- **Known Problem Pages (7 pages):** PDF pages 183, 184, 346, 368, 382, 383, 389.
- **Cross-Chapter Sample (7 pages):** PDF pages 16, 21, 73, 86, 113, 203, 261.

### Discrepancy Log (Verified against Scans)

| PDF Page | Printed Page | Scan Location | Extracted OCR Text | Visibly Supported Scan Text | Severity | Impact |
|---|---|---|---|---|---|---|
| **113** | 98 | Para 2, lines 17-21 | `ances + "8 ਕੇ ਕਵਲ ਪੰਜਾਬ ਲੈਂਡ ... 44 ਤੀਹਤ ਜਮਾਂਬਦੀ` | `ਸਚਾਈ ਦੀ ਧਾਰਨਾ ਪ੍ਰਾਪਤ ਨਹੀਂ ਹੈ ਜਿਹੜੀ ਕਿ ਕੇਵਲ ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ, 1887 ਦੀ ਧਾਰਾ 44 ਤਹਿਤ ਜਮਾਂਬੰਦੀ ਦੇ ਇੰਦਰਾਜ਼ਾਂ ਨੂੰ ਹੀ ਪ੍ਰਾਪਤ ਹੈ` | **BLOCKING** | Smashes statutory presumption of truth for Jamabandi vs Mutation. |
| **113** | 98 | Para 3, lines 26-27 | `ERT Pll 35 © ਤਰਸ ਮੁਤਾਬਕ ਤਿਨ ਮਹੀਨੇ ਦੇ \| fy ooo S00` | `ਸਬੰਧਤ ਪਟਵਾਰੀ ਨੂੰ ਧਾਰਾ 39 ਦੇ ਉਪਬੰਧ ਮੁਤਾਬਿਕ ਤਿੰਨ ਮਹੀਨੇ ਦੇ ਅੰਦਰ ਅੰਦਰ ਸੂਚਨਾ ਦੇਵੇ।` | **BLOCKING** | Loses Section 39 and corrupts the 3-month reporting deadline. |
| **113** | 98 | Para 3, lines 28-29 | `SOSH Q ABC ਆਪਣੇ ਅਖਿਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ੮' SIF ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ` | `ਕਲੈਕਟਰ ਆਪਣੇ ਅਖ਼ਤਿਆਰੀ ਅਧਿਕਾਰ ਤਹਿਤ ਇੰਤਕਾਲ ਦੀ ਫ਼ੀਸ ਦਾ ਪੰਜ ਗੁਣਾ ਜੁਰਮਾਨਾ ਵੀ ਲਗਾ ਸਕਦਾ ਹੈ` | **BLOCKING** | `ਕਲੈਕਟਰ` became `ABC` and `ਫ਼ੀਸ` became `SIF`; corrupts officer authority and fee penalty multiplier. |
| **167** | 152 | Para 1, line 11 | `TI ਪਹਿਲਾ ਦੇ ਅਧਿਕਾਰ ਅਧਿਸੂਚਨਾ ਜਿਨ੍ਹਾਂ ਦੀਆਂ set ane` | `ਦਰਜਾ ਪਹਿਲਾ ਦੇ ਅਧਿਕਾਰ ਅਧਿਸੂਚਨਾ ਜਿਨ੍ਹਾਂ ਦੀਆਂ ਨਕਲਾਂ ਕਰਮਵਾਰ` | High | Corrupts Assistant Collector 1st Grade jurisdiction wording. |
| **167** | 152 | Para 1, line 15 | `ਫ਼ੈਸਲਾ ਜ਼ਿਲਾ doe \| ਤੇ ਛੇਤੀ ਹੋ ਸਕੇ।` | `ਫ਼ੈਸਲਾ ਜ਼ਿਲ੍ਹਾ ਪੱਧਰ ਤੇ ਛੇਤੀ ਹੋ ਸਕੇ।` | Medium | Latin artifact in administrative objective clause. |
| **167** | 152 | Para 2, line 24 | `WR, ਰਾਂਹੀ ਕਰਾਰ ਦਿੱਤਾ ਗਿਆ ਹੋਵੇ, ਆਪਣੀ ਅਰਜੀ ਮਾਲ mere ਪਾਸ` | `ਹੋਵੇ, ਰਾਂਹੀ ਕਰਾਰ ਦਿੱਤਾ ਗਿਆ ਹੋਵੇ, ਆਪਣੀ ਅਰਜੀ ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ` | High | Corrupts `ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ` to `ਮਾਲ mere ਪਾਸ`. |
| **170** | 155 | Para 2, line 23 | `\| JIMS ਦਰਖਾਸਤ ਨਾਲ ਉਸ ਨੂੰ ਹਾਲੀਆ ਜਮਾਂਬੰਦੀ` | `ਆਪਣੀ ਦਰਖਾਸਤ ਨਾਲ ਉਸ ਨੂੰ ਹਾਲੀਆ ਜਮਾਂਬੰਦੀ` | Medium | Corrupts opening word of application requirement line to `JIMS`. |
| **170** | 155 | Para 2, line 26 | `ਜਿੰਨੇ ਇਸ ਵਿੱਚ ਉੱਤਰਵਾਦੀ ਹੋ\|\|। "\|` | `ਜਿੰਨੇ ਇਸ ਵਿੱਚ ਉੱਤਰਵਾਦੀ ਹੋਣ।` | Low | Corrupted terminal verb punctuation. |
| **171** | 156 | Method 2, lines 24-25 | `ਦੀ ਧਾਰਾ 34° ਤਹਿਤ ਦਰਜ ਕਰਵਾਉਣਗੀਆ ਅਤੇ ਮਾਲ ਅਫਸਰ ਪਾਸੋਂ । OO Ono... nN THA ਨ HAJ ਕਰਵਾ ਸਕਦੀਆਂ ਹਨ।` | `ਦੀ ਧਾਰਾ 34 ਤਹਿਤ ਦਰਜ ਕਰਵਾਉਣਗੀਆਂ ਅਤੇ ਮਾਲ ਅਫ਼ਸਰ ਪਾਸੋਂ ਇਸ ਨੂੰ ਮੰਜੂਰ ਕਰਵਾ ਸਕਦੀਆਂ ਹਨ।` | High | Completely loses the sanctioning clause (`ਇਸ ਨੂੰ ਮੰਜੂਰ`) into garbled Latin/symbols. |
| **172** | 157 | Para 2, line 28 | `ਜਵਾਬਦਾਵਾ UH ਕਰਨਾ ਹੋਵੇਗਾ।` | `ਜਵਾਬਦਾਵਾ ਪੇਸ਼ ਕਰਨਾ ਹੋਵੇਗਾ।` | Low | Verb `ਪੇਸ਼` corrupted to `UH` in 30-day response clause. |
| **173** | 158 | Line 4-5 | `ਲਈ ਅਗਲੀ ਤਾਰੀਖ . ® ਗਿ — 5 ਆ ਸਨ ਜ਼ਰਾ ਨ SN SY ਦ਼ ਆ ਭੈ ਧਾਰਾ 115` | `ਲਈ ਅਗਲੀ ਤਾਰੀਖ ਨਿਸਚਤ ਕਰੇਗਾ। ਧਾਰਾ 115` | Medium | Slices off `ਨਿਸਚਤ ਕਰੇਗਾ।` into a line of noise characters. |
| **174** | 159 | Para 2, line 24 | `ਹੁਕਮ UH ਕਰੇਗਾ।` | `ਹੁਕਮ ਪਾਸ ਕਰੇਗਾ।` | Low | Verb `ਪਾਸ` corrupted to `UH` in Naksha Ura order. |
| **175** | 160 | Middle lines 9-13 | `ਪਰ. . ਅਤੇ ਹੋਤ ੭੭72 ਸਿ Ca ਰਾ ਬਨਾਮ ਸੀ. ਪੰਜਾਬ) fr ਦਿ ਲੈ na oe. 132 (Am.` | `ਰਾਜਪਾਲ ਸਿੰਘ ਅਤੇ ਹੋਰ ਬਨਾਮ ਮੱਖਣ ਸਿੰਘ ਅਤੇ ਹੋਰ 2008 (1) ਐਲ. ਏ. ਆਰ. 132 (ਐਫ਼. ਸੀ. ਪੰਜਾਬ)` | **BLOCKING** | Precedent citation completely demolished; unmatchable by QA or validation. |
| **175** | 160 | Bottom lines 23-28 | `ਨੇ ੭30 ਕਲੀ 17 ਨ 9 ... ਤਜੁਖਾਸ= fr ol I init ਤਕਸੀਮ ਲਈ ਵਿਕ er ਇਦਾ ¢ ਦਿਤਾ ਸਾ` | `ਨੇ 230 ਕਨਾਲ 10 ਮਰਲੇ ਜ਼ਮੀਨ ... ਦਰਖਾਸਤ ਮਿਤੀ 12.8.2019 ਨੂੰ ਦਿੱਤੀ ਸੀ ਅਤੇ ਇਸ ਜ਼ਮੀਨ ਵਿੱਚੋਂ` | **BLOCKING** | Smashes partition land measurement (`230 ਕਨਾਲ 10 ਮਰਲੇ` -> `੭30 ਕਲੀ 17 ਨ 9`) and application filing date. |
| **179** | 164 | Line 8 | `ਹਿੱਸੇਦਾਰਾਂ ਦੇ ਆਪਸੀ ਪ੍ਰਬੰਧ ਰਾਂਹੀ € ਕਰਮਾਂ ਦਾ ਰਸਤਾ` | `ਹਿੱਸੇਦਾਰਾਂ ਦੇ ਆਪਸੀ ਪ੍ਰਬੰਧ ਰਾਂਹੀ ਦੋ ਕਰਮਾਂ ਦਾ ਰਸਤਾ` | High | Corrupts pathway measurement (`ਦੋ ਕਰਮਾਂ` -> `€ ਕਰਮਾਂ`). |
| **183** | 168 | Line 5 | `ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਤੋਂ Se ita` | `ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਤੋਂ ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ।` | High | Critical exemption from registration clause corrupted. |
| **183** | 168 | Line 27 | `AE ਅਜਿਹੀ ਸਾਂਝੀ ਰੱਖੀ ਗਈ ਜ਼ਮੀਨ ਉੱਤੇ` | `(3) ਜੇਕਰ ਅਜਿਹੀ ਸਾਂਝੀ ਰੱਖੀ ਗਈ ਜ਼ਮੀਨ ਉੱਤੇ` | Low | Clause numbering artifact preceding Section 150. |
| **184** | 169 | Line 20 | `ਤਕਸੀਮ ਦੇ a - _______ ਉੱਪਰਲੀ ਅਦਾਲਤ ਵੱਲੋਂ ਰੀਮਾਂਡ` | `ਤਕਸੀਮ ਦੇ ਕੇਸ ਉੱਪਰਲੀ ਅਦਾਲਤ ਵੱਲੋਂ ਰੀਮਾਂਡ` | Medium | Drops subject word `ਕੇਸ`. |
| **261** | 246 | Line 11 | `ਇੱਕ ਸਟੈਂਡਰਡ ਕਰਮ cc ਇੰਜ ਈਂ" ਦੀ ਹੈ` | `ਇੱਕ ਸਟੈਂਡਰਡ ਕਰਮ 66 ਇੰਚ ਦੀ ਹੈ` | **BLOCKING** | Corrupts core revenue measurement definition (`66 ਇੰਚ` -> `cc ਇੰਜ`). |
| **261** | 246 | Lines 13-19 | `ਵੱਖ ਵੱਖ ਸਾਈਜ਼ Short ert ਸਤਾ eS ... Da DORN S96 ਕੜੀਆਂ ... 5 5੦ ਐਂ ਹਨ` | `ਵੱਖ ਵੱਖ ਸਾਈਜ਼ ਦੀਆਂ ਕਰਮਾਂ ਸਥਾਨਕ ਮਾਪਾਂ ਦੇ ਹਿਸਾਬ ਨਾਲ ਵਰਤੀਆਂ ਗਈਆਂ ਹਨ ... 8 ਕੜੀਆਂ ਅਤੇ ਛੋਟੀ ਕਰਮ ਵਾਲੀ ਜਰੀਬ ਵਿੱਚ 7 ਕੜੀਆਂ ਹੁੰਦੀਆਂ ਹਨ` | **BLOCKING** | Complete gibberish across chain link counts and survey units. |
| **261** | 246 | Line 32 | `(5) 60 ਇੰਚ ਅਤੇ (6) 54 fig ਰਸ ਆਰ NIA` | `(5) 60 ਇੰਚ ਅਤੇ (6) 54 ਇੰਚ।` | High | Corrupts unit label (`ਇੰਚ` -> `fig`). |
| **346** | 331 | Rows 7 & 9 | `fret ਰਜਿਸਟਰ ... ਹਿਕਮ 3 4. ਆ ਮੁੜਵਸੇਵਾ ਵੱਲੋਂ 8 7... of India CalAVAL ... 'ਸੈਹਦਾ . ਜਿਸਥਾਂ ਉੰਤੋਦੋ ਲੀਡ` | Columns 1, 2, 3: `ਸ਼ਿਕਨੀ ਰਜਿਸਟਰ \| ਆਬਾਦੀ ਦੇਹ/ਲਾਲ ਲਕੀਰ ਅੰਦਰ ਦੀ ਜ਼ਮੀਨ ... ਮਹਿਕਮਾ ਮੁੜਵਸੇਵਾ ਵੱਲੋਂ ਭਾਰਤ ਦੀ ਵੰਡ ਤੋਂ ਬਾਦ ਤਿਆਰ ਕੀਤਾ ਗਿਆ ਸੀ \| Register containing the record ... prepared by Rehabilitation Department after partition of India` ; `ਸੇਹੱਦਾ ... A Pillar` | High | Multi-column table cell text interleaved horizontally; English and Punjabi definitions spliced together. |
| **368** | 353 | Rows 1 & 2 | `HBAS ਕਬਜ਼ਾ ਉਹ ਮਾਲਕ ਜਿਹੜੇ Those ਪਿੰਡ ਵਿੱਚ ਜ਼ਮੀਨ proprietors who ... ter fils dt of land in the` | Columns 1, 2, 3: `ਮਾਲਕਾਨ ਕਬਜ਼ਾ \| ਉਹ ਮਾਲਕ ਜਿਹੜੇ ਪਿੰਡ ਵਿੱਚ ਜ਼ਮੀਨ ਦੇ ਮਾਲਕ ਹੋਣ ਪਰ ਉਨ੍ਹਾਂ ਦਾ ਪਿੰਡ ਦੀ ਸਾਂਝੀ ਜ਼ਮੀਨ ਵਿੱਚ ਹਿੱਸਾ ਨਹੀਂ ਹੁੰਦਾ \| Those proprietors who are the owners of land in the village but not allowed any share in the shamilat` | High | Horizontal column bleeding destroys dictionary term-definition mapping. |
| **382** | 367 | Entire page | `— -ਅਤਸਸਸਸਸ ਸ਼ਸਸੁੁੁੁਰਲਨਹਭ਼ਭਟਅਿ_- 1 -200000000/01677301 ... 11 ਸਿੰਘ ਚਾਹੀ` | 90° CCW rotated Khasra table: Khasra numbers `2//12`, `13`, `14`, `15`, `16`, total `ਕਿਤਾ 5 40-0 ਚਾਹੀ`, Khewat `243`, Owner `ਗੁਰਮੀਤ ਸਿੰਘ ਹਿੱਸੇਦਾਰ`. | **BLOCKING** | Rotated table failure; output is pure non-semantic garbage. |
| **383** | 368 | Entire page | `[BE \|\| FE \|ਨਾਮਮਾਲਕਤੇਹਾਲ]\|ਕਾਸ਼ਕਕਾਰ [ਇ \|] \| ਇੰ \|B \|B [& \| ... [1458 [760 ਚਾਰ teeta` | 90° CCW / upside-down 12-column Jamabandi sample table (`ਅਨੁਲੱਗ-15`). | **BLOCKING** | Rotated table failure; complete structural and data loss. |
| **389** | 374 | Entire page | `ਖਸਤਾ Taras of os os ... ਲਤ ਨ 533 oF AS mew 'ਚਪ੍ਟ Fae =5 oF ਕਾਸ਼ਤ` | Landscape Khasra Girdawari register (`ਅਨੁਲੱਗ-18`) with 8 columns. | **BLOCKING** | Rotated table failure; survey inspection records completely lost. |

---

## 4. Analysis of Specific Critical Concerns

### 4.1. Page 167: DRO Officer Reference and Notification Date
- **Audit Target:** Did the repair restore the deciding officer reference and notification date `1.12.2008`?
- **Finding:** **CONFIRMED RESTORED.**
  In `reports/ocr_repair/ocr_selected/page_0167.json`, lines 12–15:
  ```
  ਕਰਨ ਦੇ ਅਧਿਕਾਰ ਕੇਵਲ ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ ਨੂੰ ਨੋਟੀਫਿਕੇਸ਼ਨ ਮਿਤੀ
  ___1.12.2008 ਰਾਂਹੀ ਦਿੱਤੇ ਗਏ ਹਨ ਜਿਸ ਦੀ ਨਕਲ ਅਨੁਲੱਗ-8 ਹੈ।
  ```
  Both `ਜ਼ਿਲ੍ਹਾ ਮਾਲ ਅਫ਼ਸਰਾਂ` and `1.12.2008` are present in `text_raw`, `text_clean`, and reached staged chunk `3dead4aade28254d`.
- **Remaining Weakness:** Preceding and succeeding lines contain scan edge artifacts (`TI ਪਹਿਲਾ` instead of `ਦਰਜਾ ਪਹਿਲਾ`, `set ane` instead of `ਨਕਲਾਂ ਕਰਮਵਾਰ`, `ਫ਼ੈਸਲਾ ਜ਼ਿਲਾ doe` instead of `ਫ਼ੈਸਲਾ ਜ਼ਿਲ੍ਹਾ ਪੱਧਰ`, `ਮਾਲ mere ਪਾਸ` instead of `ਮਾਲ ਅਫ਼ਸਰ ਪਾਸ`).

### 4.2. Page 183: Section 150 (Unauthorized Possession of Common Land)
- **Audit Target:** Did the repair restore Section 150 for eviction of unauthorized encroachers on partitioned/joint land?
- **Finding:** **CONFIRMED RESTORED.**
  In `reports/ocr_repair/ocr_selected/page_0183.json`, lines 27–31:
  ```
  AE ਅਜਿਹੀ ਸਾਂਝੀ ਰੱਖੀ ਗਈ ਜ਼ਮੀਨ ਉੱਤੇ ਕੋਈ ਵੀ
  ਸਹਿ-ਹਿੱਸੇਦਾਰ ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾ ਕਰ ਲਵੇ ਤਾਂ ਦੂਜਾ ਸਹਿ-ਹਿੱਸੇਦਾਰ ਧਾਰਾ
  150 ਤਹਿਤ: ਮਾਲ ਅਫ਼ਸਰ ਨੂੰ ਇਸ ਨਾਜਾਇਜ਼ ਕਬਜ਼ੇ ਨੂੰ ਖਾਲੀ ਕਰਵਾਉਣ
  BE ਦਰਖਾਸਤ ਦੇ ਸਕਦਾ ਹੈ ਅਤੇ ਮਾਲ ਅਫ਼ਸਰ ਅਜਿਹਾ ਨਾਜਾਇਜ਼
  ਕਬਜ਼ਾ ਖਾਲੀ ਕਰਵਾ ਸਕਦਾ ਹੈ।
  ```
  Section `150` is present and successfully indexed into staged chunk `4edfd7e960f3923e`.
- **Remaining Weakness:** Registration exemption sentence still loses `ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ` (`ਰਜਿਸਟ੍ਰੇਸ਼ਨ ਤੋਂ Se ita`).

### 4.3. Sideways Tables (Pages 382, 383, 389)
- **Audit Target:** Can per-line extraction handle sideways/rotated tables?
- **Finding:** **COMPLETE EXTRACTION BREAKDOWN.**
  The per-line slicer does not detect that these pages are oriented 90 degrees counter-clockwise relative to the page bounding box. It slices horizontal swaths across vertical columns, cutting characters in half and emitting strings like `-200000000/01677301 22-90007007779ਰ0977777557772੍‌ਸਸਭਝ7575751`.
  Because character length exceeds 40 and Tesseract reports 0 empty lines, the ingestion pipeline marks these pages `quality: ok`! This confirms the heuristic flaw identified in `AUDIT.md`.

### 4.4. Bilingual Glossaries (Pages 346, 368)
- **Audit Target:** Preservation of row-column associations.
- **Finding:** **TABLE FLATTENING & CROSS-LANGUAGE BLEEDING.**
  The pipeline extracts text across the entire width of the page bounding box without column division. As a result, English translation text from column 3 is concatenated directly onto Punjabi explanations from column 2, creating mixed Punjabi-English sentences that confuse embedding semantic representations.

---

## 5. Staged Database Read-Only Verification (Task 6)

The staged database `reports/ocr_repair/jarvis.staged.db` was inspected using the application's verification suite:

1. **Gate Verification (`check_import`):**
   - SQLite PRAGMA `integrity_check`: `ok`.
   - SQLite PRAGMA `foreign_key_check`: 0 violations.
   - Vector completeness: 3,160 chunks in DB, 3,160 non-null vectors of dimension 384. Zero orphan records.
2. **Law Corpus Isolation:**
   - Compared against `reports/ocr_repair/backup/jarvis.production-20261013-141120.db`:
     - Exactly 27 law documents in both databases.
     - Exactly 2,213 law chunks, vectors, and BM25 tokens in both databases.
     - Byte-level identity confirmed; the OCR repair did not contaminate the statutory law corpus.
3. **Review Provenance (`page_reviews` table):**
   - Exactly 6 reviews recorded: pages 167, 170, 183, 184, 321, 334.
   - All 6 records have `status = 'needs_review'`.
   - Reviewer field explicitly warns: `AI assistant (Claude) visual comparison against scan; NOT human-reviewed`.
   - Text SHA-256 and image SHA-256 exactly match current `pages` table records.

---

## 6. Categorization: Blocking Errors vs. Minor Spelling Errors

### Category A: Blocking Errors (Must not certify as legally reliable or high accuracy)
1. **Corrupted Statutory Deadlines & Penalty Powers (Page 113):**
   - Discretionary fine power of the Collector up to 5x mutation fee (`ਕਲੈਕਟਰ` -> `ABC`, `ਫ਼ੀਸ` -> `SIF`).
   - 3-month statutory reporting period under Section 39.
   - Section 44 presumption of truth.
2. **Corrupted Precedent Citations & Land Areas (Page 175):**
   - Precedent `ਰਾਜਪਾਲ ਸਿੰਘ ਅਤੇ ਹੋਰ ਬਨਾਮ ਮੱਖਣ ਸਿੰਘ... 2008 (1) ਐਲ. ਏ. ਆਰ. 132 (ਐਫ਼. ਸੀ. ਪੰਜਾਬ)`.
   - Land measurement `230 ਕਨਾਲ 10 ਮਰਲੇ` -> `੭30 ਕਲੀ 17 ਨ 9`.
3. **Corrupted Fundamental Revenue Measurement Units (Page 261):**
   - Standard Karam length `66 ਇੰਚ` -> `cc ਇੰਜ`.
4. **Complete Table Breakdown on Rotated Annexures (Pages 382, 383, 389):**
   - Jamabandi, Khasra, and Girdawari tables rendered as non-semantic noise strings while falsely flagged `quality: ok`.

### Category B: High-Priority Recoverable Errors
1. **Omitted Sanction Clause (Page 171):** `ਇਸ ਨੂੰ ਮੰਜੂਰ ਕਰਵਾ ਸਕਦੀਆਂ ਹਨ` turned into `। OO Ono... nN THA ਨ HAJ`.
2. **Registration Exemption Clause (Page 183):** `ਛੋਟ ਪ੍ਰਾਪਤ ਹੈ` turned into `Se ita`.
3. **Corrupted Assistant Collector Designation (Page 167):** `ਦਰਜਾ ਪਹਿਲਾ` turned into `TI ਪਹਿਲਾ`, `ਮਾਲ ਅਫ਼ਸਰ` turned into `ਮਾਲ mere`.
4. **Pathway Dimension (Page 179):** `ਦੋ ਕਰਮਾਂ ਦਾ ਰਸਤਾ` turned into `€ ਕਰਮਾਂ ਦਾ ਰਸਤਾ`.
5. **Hindu Succession Act Section 30 Bottom Line Cutoff (Page 73):** Cutoff by vertical bounding window.

### Category C: Minor Spelling & Punctuation Noise (Tolerated by Dense Retrieval)
1. `ਚਪਟਰ` vs `ਚੈਪਟਰ` (Page 167)
2. `ਪ੍ਵਾਸੀ` vs `ਪ੍ਰਵਾਸੀ` (Page 167)
3. `JIMS ਦਰਖਾਸਤ` vs `ਆਪਣੀ ਦਰਖਾਸਤ` (Page 170)
4. `ਹੋ||। "|` vs `ਹੋਣ।` (Page 170)
5. `ਜਵਾਬਦਾਵਾ UH ਕਰਨਾ` vs `ਜਵਾਬਦਾਵਾ ਪੇਸ਼ ਕਰਨਾ` (Page 172)
6. `ਹੁਕਮ UH ਕਰੇਗਾ` vs `ਹੁਕਮ ਪਾਸ ਕਰੇਗਾ` (Page 174)
7. `ਨਕਸ਼ਾ ਉ` vs `ਨਕਸ਼ਾ ੳ` (Page 174)
8. `H'S ਅਧਿਕਾਰੀਆਂ` vs `ਮਾਲ ਅਧਿਕਾਰੀਆਂ` (Page 252)

---

## 7. Recommended Next Steps (For Subsequent Repair Phase)

1. **Do not treat `tessdata_best per-line split120` as sufficient for tables or rotated annexures:**
   Implement a rotation preprocessing step (90° CCW / CW detection via Tesseract OSD or aspect-ratio heuristics) and specialized table extraction for Annexures 15, 18, and Jamabandi templates.
2. **Targeted Transcription for Confirmed Failing Pages:**
   Pages 113, 167, 171, 175, 183, 261, 382, 383, and 389 require manual or high-fidelity targeted transcription rather than automated line slicing.
3. **Adjust Top Margin Slicing for Printed Page Labels:**
   52 body pages missed printed labels because the top 100 pixels were skipped or merged into chapter headings. Broadening `cands` or scanning the top 150 pixels will recover verified page mappings.
4. **Preserve System Boundaries:**
   Continue to enforce `--baseline-db` import checks to ensure the statutory law corpus remains completely isolated from OCR experiments.
