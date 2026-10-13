import numpy as np
from PIL import Image, ImageDraw

from revenue_jarvis.ocr.engine import remove_rulings, segment_lines


def _page(table=False):
    img = Image.new("L", (1200, 900), 255)
    d = ImageDraw.Draw(img)
    for i in range(8):
        y = 80 + i * 90
        for x in range(100, 1000, 40):
            d.rectangle([x, y, x + 28, y + 40], fill=0)        # word-like blobs, 40 px tall
    if table:
        for x in (60, 600, 1100):
            d.line([x, 40, x, 860], fill=0, width=8)           # vertical table rulings
        for y in (40, 860):
            d.line([60, y, 1100, y], fill=0, width=3)
    return img


def test_segments_plain_lines():
    assert len(segment_lines(_page())) == 8


def test_table_rulings_removed_before_segmentation():
    img = _page(table=True)
    assert len(segment_lines(img)) <= 2          # borders glue everything into one band
    assert len(segment_lines(remove_rulings(img))) == 8


def test_remove_rulings_keeps_text_ink():
    img = _page(table=True)
    before = (np.asarray(_page()) < 150).sum()
    after = (np.asarray(remove_rulings(img)) < 150).sum()
    assert abs(after - before) / before < 0.05
