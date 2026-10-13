# OCR coverage report

Book: S. L. Bhumbak, *Zameen Di Guide* (389 scanned pages, no text layer).
Engine: Tesseract `pan+eng`, one line at a time at 300 dpi, after removing table rulings. Per-page detail: `reports/ocr_coverage.csv`.

| Measure | Value |
|---|---|
| Pages processed | 389 of 389 |
| Pages with usable text | 387 |
| Pages with no text (map, rotated sample form) | 2 (PDF p. 30, 382) |
| Pages with an unreadable line | 1 |
| Text lines read | 12,146 |
| Lines that failed every attempt | 1 (0.008%) |
| Lines rescued by the fallback mode (lower confidence) | 2,101 (17.3%) |
| Body pages with an OCR-verified printed page number | 309 of 374 |

## How to read this

* "Lines read" means Tesseract returned text for the line; it doesn't mean every character is right. Gurmukhi OCR typically drops or swaps some vowel signs (for example ਮੁ/ਮ, ਨੂੰ/ਨੰ). Search tolerates this because it combines meaning-based vectors with keywords, but **always open the cited page before relying on an exact word or number**.
* Pages where 10 or more lines needed the fallback mode are the least reliable: PDF p. 3, 8, 18, 27, 42, 45, 75, 87, 88, 90, 91, 92, 95, 97, 104, 105, 108, 111, 120, 123, 128, 129, 131, 132, 144, 149, 150, 152, 157, 159, 161, 162, 163, 172, 175, 181, 186, 189, 190, 191, 193, 195, 199, 204, 206, 207, 212, 213, 239, 241, 243, 252, 271, 275, 280, 281, 282, 284, 287, 289, 301, 324, 334, 335, 336.
* Front matter (PDF p. 1–15: cover, foreword, contents) is stored but never used as evidence.
* A citation shows "Book p.N" only when the number printed on the page was read and agrees with the book's offset (printed = PDF − 15); otherwise only the PDF page is shown.
