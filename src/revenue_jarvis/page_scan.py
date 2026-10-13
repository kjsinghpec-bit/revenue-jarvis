"""Serve only the original book scan whose checksum matches the indexed source."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile


@lru_cache(maxsize=4)
def _hash_file(path: str, size: int, mtime: int) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def matching_scan(path: Path | None, expected_sha256: str | None) -> bool:
    if not path or not expected_sha256:
        return False
    try:
        stat = path.stat()
        return _hash_file(str(path.resolve()), stat.st_size, stat.st_mtime_ns) == expected_sha256
    except OSError:
        return False


def render_png(path: Path, page: int) -> bytes:
    try:
        import pymupdf
    except ImportError:
        # The recovered local runtime has Poppler but not PyMuPDF.
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'page'
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '110',
                            '-singlefile', '-png', str(path.resolve()), str(target)],
                           check=True, capture_output=True, timeout=30)
            return target.with_suffix('.png').read_bytes()
    with pymupdf.open(str(path)) as document:
        if not 1 <= page <= document.page_count:
            raise ValueError('No such PDF page')
        return document[page - 1].get_pixmap(dpi=110).tobytes('png')
