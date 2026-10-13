"""Cross-references: the book cites statutes ("ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ, 1887 ਦੀ ਧਾਰਾ 117", "ਰੂਲ 6(1)(ਬੀ)").
Reading those citations out of the retrieved book pages lets the statute pool follow the book,
instead of competing with it. Only a citation that names (or sits next to) a known act is used."""
from __future__ import annotations

import re

from .text import ascii_digits

# (pattern seen in the Gurmukhi text or an English question) -> corpus short_name
ACT_HINTS: list[tuple[str, str]] = [
    (r"ਲੈਂਡ\s*ਰੈਵੀਨਿ[ਊਉ]\s*ਐਕਟ|land revenue act|\bplra\b", "PLRA 1887"),
    (r"(?:ਕੋਮਨ|ਕਾਮਨ)\s*ਲੈਂਡ[ਜ਼ਜ]*.{0,30}?ਰੂਲ|common lands? .{0,30}rules|\b1964\b", "PVCL Rules 1964"),
    (r"(?:ਕੋਮਨ|ਕਾਮਨ)\s*ਲੈਂਡ|common lands?|1961\s*ਦੇ\s*ਐਕਟ|\b1961\b", "PVCL Act 1961"),
    (r"ਹੋਲਡਿੰਗ|ਕੰਸੋਲੀਡੇਸ਼ਨ|consolidation|\b1948\b", "EPH Consolidation Act 1948 + Rules 1949"),
    (r"ਰਜਿਸਟ੍?ਰੇਸ਼ਨ\s*ਐਕਟ|registration act|\b1908\b", "Registration Act 1908"),
    (r"ਸਟੈਂਪ\s*ਐਕਟ|ਅਸ਼ਟਾਮ\s*ਐਕਟ|stamp act|\b1899\b", "Stamp Act 1899"),
    (r"ਸ[ੁ]?ਕਸੈਸ਼ਨ|succession act", "HSA 1956"),
    (r"ਟਰਾਂਸਫਰ\s*ਆਫ|transfer of property|\b1882\b", "TPA 1882"),
    (r"ਟੈਨੇਂਸੀ|ਟੈਨੈਂਸੀ|tenancy act", "PTA 1887"),
    (r"ਕੰਮ?ਪਨਸੇਸ਼ਨ|ਐਕੋਜੀਸ਼ਨ|fair compensation|land acquisition|rfctlarr|\b2013\b", "RFCTLARR 2013"),
    (r"ਪਬਲਿਕ\s*ਪ੍ਰੀਮਿਸਿਜ਼|public premises", "PPPL Eviction Act 1973"),
    (r"ਲੈਂਡ\s*ਰਿਕਾਰਡ\s*ਮੈਨ[ੁੂ]?ਅਲ|land records manual", "PLRM"),
]
# When a passage cites "ਧਾਰਾ 7" / "ਰੂਲ 6" without naming the act, its subject decides (ordered by specificity).
TOPIC_DEFAULT: list[tuple[str, str]] = [
    (r"ਸ਼ਾਮਲਾਤ|ਪੰਚਾਇਤ", "PVCL Act 1961"),
    (r"ਮੁਰੱਬੇਬੰਦੀ|ਚੱਕਬੰਦੀ|ਮੁਰੱਬਾਬੰਦੀ", "EPH Consolidation Act 1948 + Rules 1949"),
    (r"ਮੁਆਵਜ਼|ਅਵਾਰਡ|ਐਕਵਾਇਰ|ਐਕੁਆਇਰ|ਭੋਂ ਪ੍ਰਾਪਤੀ", "RFCTLARR 2013"),
    (r"ਤਕਸੀਮ|ਇੰਤਕਾਲ|ਜਮ੍ਹਾਂਬੰਦੀ|ਮਾਲ ਅਧਿਕਾਰੀ", "PLRA 1887"),
]
_SEC = r"(\d{1,3}(?:\.\d{1,2})?(?:-?[A-Z])?)"
CITE_PATTERNS = [
    re.compile(r"(?:ਧਾਰਾ|ਧਾਰਾਂ|ਸੈਕਸ਼ਨ|section|sec\.|s\.)\s*" + _SEC, re.I),
    re.compile(r"(?:ਰੂਲ|rule)\s*" + _SEC, re.I),
    re.compile(r"(?:ਪੈਰਾ|para(?:graph)?)\s*" + _SEC, re.I),
]
RANGE = re.compile(r"(\d{1,3})\s*ਤੋਂ\s*(?:ਲੈ\s*ਕੇ\s*)?(\d{1,3})\s*ਤੱਕ\s*(?:ਦੀਆਂ\s*)?ਧਾਰਾਵਾਂ|sections?\s*(\d{1,3})\s*(?:to|-)\s*(\d{1,3})", re.I)


def _act_near(text: str, pos: int, window: int = 180) -> str | None:
    """Nearest act named before the citation (or just after it, e.g. '... ਧਾਰਾ 7, 1961 ਦੇ ਐਕਟ')."""
    before = text[max(0, pos - window): pos]
    best: tuple[int, str] | None = None
    for pat, name in ACT_HINTS:
        for m in re.finditer(pat, before, re.I):
            if best is None or m.end() > best[0]:
                best = (m.end(), name)
    if best:
        return best[1]
    after = text[pos: pos + 60]
    for pat, name in ACT_HINTS:
        if re.search(pat, after, re.I):
            return name
    return None


def extract_citations(text: str) -> list[tuple[str, str]]:
    """[(short_name, section)] in reading order, de-duplicated. Rules -> the act's Rules where known."""
    text = ascii_digits(text)
    default = next((name for pat, name in TOPIC_DEFAULT if re.search(pat, text)), None)
    found: list[tuple[int, str, str]] = []
    for m in RANGE.finditer(text):
        a, b = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
        act = _act_near(text, m.start())
        if act and 0 < b - a <= 40:
            found += [(m.start(), act, str(n)) for n in range(a, b + 1)]
    for kind, pat in enumerate(CITE_PATTERNS):
        for m in pat.finditer(text):
            act = _act_near(text, m.start()) or (default if kind < 2 else None)
            if not act:
                continue
            if kind == 1 and act == "PVCL Act 1961":
                act = "PVCL Rules 1964"
            found.append((m.start(), act, m.group(1)))
    out: list[tuple[str, str]] = []
    for _, act, sec in sorted(found):
        if (act, sec) not in out:
            out.append((act, sec))
    return out
