"""Regenerate the verification reports from the knowledge base:
docs/OCR_COVERAGE.md, docs/SOURCES.md and reports/ocr_coverage.csv.

    python scripts/make_reports.py [--db data/jarvis.db]
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "jarvis.db"))
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    (ROOT / "reports").mkdir(exist_ok=True)

    pages = con.execute("SELECT pdf_page, printed_label, label_source, n_lines, failed_lines, recovered_lines, quality, "
                        "is_front_matter, length(text_clean) AS chars FROM pages ORDER BY pdf_page").fetchall()
    with (ROOT / "reports" / "ocr_coverage.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(pages[0].keys())
        w.writerows([tuple(r) for r in pages])
    n = len(pages)
    body = [p for p in pages if not p["is_front_matter"]]
    q = lambda k: sum(1 for p in pages if p["quality"] == k)  # noqa: E731
    lines = sum(p["n_lines"] or 0 for p in pages)
    failed = sum(p["failed_lines"] or 0 for p in pages)
    rescued = sum(p["recovered_lines"] or 0 for p in pages)
    labelled = sum(1 for p in body if p["printed_label"])
    empty = [str(p["pdf_page"]) for p in pages if p["quality"] == "empty"]
    heavy = [str(p["pdf_page"]) for p in pages if (p["recovered_lines"] or 0) >= 10]
    md = f"""# OCR coverage report

Book: S. L. Bhumbak, *Zameen Di Guide* (389 scanned pages, no text layer).
Engine: Tesseract `pan+eng`, one line at a time at 300 dpi, after removing table rulings. Per-page detail: `reports/ocr_coverage.csv`.

| Measure | Value |
|---|---|
| Pages processed | {n} of 389 |
| Pages with usable text | {q('ok') + q('partial')} |
| Pages with no text (map, rotated sample form) | {q('empty')} (PDF p. {', '.join(empty) or '-'}) |
| Pages with an unreadable line | {q('partial')} |
| Text lines read | {lines:,} |
| Lines that failed every attempt | {failed} ({failed / max(lines, 1):.3%}) |
| Lines rescued by the fallback mode (lower confidence) | {rescued:,} ({rescued / max(lines, 1):.1%}) |
| Body pages with an OCR-verified printed page number | {labelled} of {len(body)} |

## How to read this

* "Lines read" means Tesseract returned text for the line; it doesn't mean every character is right. Gurmukhi OCR typically drops or swaps some vowel signs (for example ਮੁ/ਮ, ਨੂੰ/ਨੰ). Search tolerates this because it combines meaning-based vectors with keywords, but **always open the cited page before relying on an exact word or number**.
* Pages where 10 or more lines needed the fallback mode are the least reliable: PDF p. {', '.join(heavy[:80])}{' …' if len(heavy) > 80 else ''}.
* Front matter (PDF p. 1–15: cover, foreword, contents) is stored but never used as evidence.
* A citation shows "Book p.N" only when the number printed on the page was read and agrees with the book's offset (printed = PDF − 15); otherwise only the PDF page is shown.
"""
    (ROOT / "docs" / "OCR_COVERAGE.md").write_text(md)

    docs = con.execute("SELECT d.short_name, d.title, d.jurisdiction, d.doc_type, d.source_url, d.complete, d.notes, "
                       "COUNT(c.id) AS chunks, COUNT(DISTINCT c.section) AS sections FROM documents d "
                       "LEFT JOIN chunks c ON c.doc_id=d.id WHERE d.kind='law' GROUP BY d.id ORDER BY d.jurisdiction DESC, d.short_name").fetchall()
    rows = "\n".join(
        f"| {d['short_name']} | {d['jurisdiction']} | {d['doc_type']} | {d['sections']} | {'yes' if d['complete'] else '**check**'} | "
        f"[official page]({d['source_url']}) | {(d['notes'] or '').replace('|', '/')[:220]} |" for d in docs)
    (ROOT / "docs" / "SOURCES.md").write_text(f"""# Statute sources (secondary)

The book is the primary source. These {len(docs)} official texts support it. Each was read from the official URL shown, using an
Internet Archive snapshot when the live site couldn't be reached from the build machine; the snapshot date is in the notes.

| Short name | Jurisdiction | Type | Sections found | Complete | Source | Notes |
|---|---|---|---|---|---|---|
{rows}

**Not collected:** Punjab RFCTLARR Rules 2014 (no official copy found), Punjab Land Records Manual chapters 1–4, 8, 15, 16 (no archived copy).
**Version cautions:** the Consolidation text is the Haryana-applicable version; the Stamp Act text is current only to about 2001;
the Registration and Tenancy texts may lack recent Punjab amendments. Jarvis shows these cautions beside any answer that cites them.
""")
    print("reports written")


if __name__ == "__main__":
    main()
