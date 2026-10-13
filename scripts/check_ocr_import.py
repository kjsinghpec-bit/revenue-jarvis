#!/usr/bin/env python3
"""Read-only staged OCR import gate. Exit 1 on index/page consistency failures."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from revenue_jarvis.db import connect
from revenue_jarvis.ocr_review import check_import


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--baseline-db', type=Path)
    parser.add_argument('--expected-pages', type=Path, help='JSON list: doc_id, pdf_page, text_sha256, optional printed_page')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    expected = json.loads(args.expected_pages.read_text()) if args.expected_pages else None
    con = connect(args.db, readonly=True)
    baseline = connect(args.baseline_db, readonly=True) if args.baseline_db else None
    try:
        report = check_import(con, expected, baseline)
    finally:
        con.close()
        if baseline:
            baseline.close()
    result = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result + '\n')
    print(result)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
