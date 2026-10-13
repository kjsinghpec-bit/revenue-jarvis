"""Resumable full-book OCR. One JSON per page in data/book/ocr/. Safe to re-run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_jarvis.ocr.engine import TesseractOCR  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tessdata")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=0)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--offset", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ocr = TesseractOCR(Path(a.tessdata) if a.tessdata else None)
    doc = pymupdf.open(a.pdf)
    end = a.end or doc.page_count
    for p in range(a.start + a.offset, end + 1, a.step):
        f = out / f"page_{p:04d}.json"
        if f.exists():
            continue
        t = time.time()
        pix = doc[p - 1].get_pixmap(dpi=300, colorspace=pymupdf.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        res = ocr.page(img)
        rec = {
            "pdf_page": p,
            "engine": "tesseract-5 pan+eng per-line",
            "text_raw": res.text,
            "lines": [{"y0": ln.y0, "y1": ln.y1, "text": ln.text, "scale": ln.scale, "ok": ln.ok} for ln in res.lines],
            "n_lines": len(res.lines),
            "failed_lines": res.failed_lines,
            "recovered_psm13": sum(1 for ln in res.lines if ln.scale == -13.0),
            "image_sha256": hashlib.sha256(pix.samples).hexdigest(),
            "seconds": round(time.time() - t, 2),
        }
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False))
        tmp.replace(f)
        print(p, rec["n_lines"], rec["failed_lines"], rec["seconds"], flush=True)


if __name__ == "__main__":
    main()
