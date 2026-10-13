"""Local, free OCR for scanned Gurmukhi/English pages.

Why per-line OCR: on this book, Tesseract's page layout analysis silently drops
whole text lines (reproduced on PDF p.119). Dropping a line of legal text is
unacceptable, so we segment lines ourselves with a horizontal ink profile, OCR
every line image in ONE tesseract process (list-file mode), and re-try any line
that comes back empty at two other scales. Lines that still fail are flagged,
never silently lost.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

INK_THRESHOLD = 150          # grey level below which a pixel is "ink"
MIN_LINE_PX = 8              # ignore specks shorter than this
MERGE_GAP_PX = 12            # join a matra/dot band to the line just above
PAD_PX = 6
RETRY_SCALES = (2 / 3, 4 / 3)


@dataclass
class LineResult:
    y0: int
    y1: int
    text: str
    scale: float = 1.0
    ok: bool = True


@dataclass
class PageOCR:
    lines: list[LineResult] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(ln.text for ln in self.lines if ln.text)

    @property
    def failed_lines(self) -> int:
        return sum(1 for ln in self.lines if not ln.ok)


def _longest_runs(mask: np.ndarray) -> np.ndarray:
    """Longest run of True along axis 0 for every column."""
    h, w = mask.shape
    best = np.zeros(w, dtype=np.int32)
    cur = np.zeros(w, dtype=np.int32)
    for y in range(h):
        cur = np.where(mask[y], cur + 1, 0)
        best = np.maximum(best, cur)
    return best


def remove_rulings(img: Image.Image) -> Image.Image:
    """Whiten table borders and long rules so they don't glue all text lines into one band.
    Text strokes are short; ruling lines are long and thin."""
    g = np.asarray(img.convert("L")).copy()
    ink = g < INK_THRESHOLD
    h, w = ink.shape
    vcols = _longest_runs(ink) > max(60, int(0.06 * h))          # long vertical strokes
    hrows = _longest_runs(ink.T) > max(80, int(0.25 * w))        # long horizontal strokes
    if vcols.any():
        # only remove pixels that belong to a long vertical run, not the whole column
        for x in np.where(vcols)[0]:
            col = ink[:, x]
            y = 0
            while y < h:
                if col[y]:
                    y2 = y
                    while y2 < h and col[y2]:
                        y2 += 1
                    if y2 - y > max(60, int(0.06 * h)):
                        g[y:y2, max(0, x - 1):x + 2] = 255
                    y = y2
                else:
                    y += 1
    for yy in np.where(hrows)[0]:
        row = ink[yy]
        x = 0
        while x < w:
            if row[x]:
                x2 = x
                while x2 < w and row[x2]:
                    x2 += 1
                if x2 - x > max(80, int(0.25 * w)):
                    g[max(0, yy - 1):yy + 2, x:x2] = 255
                x = x2
            else:
                x += 1
    return Image.fromarray(g)


def segment_lines(img: Image.Image) -> list[tuple[int, int]]:
    """Return (y0, y1) bands of text lines using a horizontal ink profile."""
    g = np.asarray(img.convert("L"))
    ink = (g < INK_THRESHOLD).sum(axis=1)
    if ink.max() == 0:
        return []
    on = ink > max(3, ink.max() * 0.01)
    segs: list[tuple[int, int]] = []
    start = None
    for y, v in enumerate(on):
        if v and start is None:
            start = y
        elif not v and start is not None:
            if y - start > MIN_LINE_PX:
                segs.append((start, y))
            start = None
    if start is not None and len(on) - start > MIN_LINE_PX:
        segs.append((start, len(on)))
    merged: list[tuple[int, int]] = []
    for a, b in segs:
        if merged and a - merged[-1][1] < MERGE_GAP_PX and (b - a) < 35:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return merged


def _tight(img: Image.Image) -> Image.Image:
    g = np.asarray(img)
    cols = np.where((g < INK_THRESHOLD).sum(axis=0) > 0)[0]
    if len(cols) == 0:
        return img
    return img.crop((max(0, int(cols[0]) - 20), 0, min(img.width, int(cols[-1]) + 20), img.height))


class TesseractOCR:
    def __init__(self, tessdata_dir: Path | None = None, langs: str = "pan+eng", timeout: int = 300):
        if not shutil.which("tesseract"):
            raise RuntimeError("tesseract not found. Install with: brew install tesseract")
        self.tessdata_dir = tessdata_dir
        self.langs = langs
        self.timeout = timeout

    def _batch(self, images: list[Image.Image], psm: int = 7) -> list[str]:
        if not images:
            return []
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for i, im in enumerate(images):
                p = Path(td) / f"l{i:04d}.png"
                im.save(p)
                paths.append(str(p))
            lst = Path(td) / "list.txt"
            lst.write_text("\n".join(paths) + "\n")
            cmd = ["tesseract", str(lst), "-", "-l", self.langs, "--psm", str(psm)]
            if self.tessdata_dir:
                cmd += ["--tessdata-dir", str(self.tessdata_dir)]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, check=False)
            if out.returncode != 0:
                raise RuntimeError(f"tesseract failed: {out.stderr.strip()[:300]}")
        parts = out.stdout.split("\f")
        parts = (parts + [""] * len(images))[: len(images)]
        return [" ".join(p.split()) for p in parts]

    def page(self, img: Image.Image) -> PageOCR:
        grey = remove_rulings(img.convert("L"))
        bands = segment_lines(grey)
        # a band taller than ~3 text lines means segmentation failed (pictures, dense tables): split it evenly
        fixed: list[tuple[int, int]] = []
        for a, b in bands:
            if b - a > 170:
                n = max(2, round((b - a) / 60))
                step = (b - a) / n
                fixed += [(int(a + i * step), int(a + (i + 1) * step)) for i in range(n)]
            else:
                fixed.append((a, b))
        bands = fixed
        crops = [_tight(grey.crop((0, max(0, a - PAD_PX), grey.width, min(grey.height, b + PAD_PX)))) for a, b in bands]
        texts = self._batch(crops)
        res = [LineResult(a, b, t) for (a, b), t in zip(bands, texts, strict=False)]
        for scale in RETRY_SCALES:
            todo = [i for i, r in enumerate(res) if not r.text and bands[i][1] - bands[i][0] > 20]
            if not todo:
                break
            scaled = [crops[i].resize((max(1, int(crops[i].width * scale)), max(1, int(crops[i].height * scale)))) for i in todo]
            for i, t in zip(todo, self._batch(scaled), strict=False):
                if t:
                    res[i].text, res[i].scale = t, scale
        # Last resort: raw-line mode (psm 13) recovers lines the LSTM line mode returns empty for.
        todo = [i for i, r in enumerate(res) if not r.text and bands[i][1] - bands[i][0] > 20]
        for i, t in zip(todo, self._batch([crops[i] for i in todo], psm=13), strict=False):
            if t:
                res[i].text, res[i].scale = t, -13.0  # marker: recovered with psm 13 (lower trust)
        for i, r in enumerate(res):
            if not r.text and bands[i][1] - bands[i][0] > 20:
                r.ok = False
        return PageOCR(res)
