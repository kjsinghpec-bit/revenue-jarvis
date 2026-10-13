"""Load official bare acts / rules / manuals (secondary sources) as section-level chunks."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..text import nfc

# Section / rule / manual-paragraph heads at line start, e.g. "117. Partition", "13A Penalties", "18.1 Private",
# "Section 7.", "1 [7. Power ..." (amendment footnote marker before the bracket).
FOOTNOTE_BRACKET = re.compile(r"^(\s*)(?:\{\^\d+\}|\d{1,2})?\s*\[\s*(?=\d)", re.M)
HEAD_RE = re.compile(
    r"^\s*(?:(?:Section|Sec\.|Rule|Para(?:graph)?)\s+)?(?:\d{1,2}\s+(?=\d{1,3}[A-Z]{0,2}\s*[.:\-\u2013]))?"
    r"(\d{1,3}(?:\.\d{1,2})?(?:-?[A-Z]{1,2})?)\s*[.:\-\u2013)]?\s*(?=[A-Za-z\u201c\"\[(])"
    # amendment footnotes ("4 Substituted by ...", "6 Clause (b) omitted ...") are not section heads
    r"(?!(?:Sub[ -]?[Cc]lause|Substituted|Omitted|Inserted|Added|Amended|Clause|Proviso|Pb\.|Hr\.|Rule \d|Words|Ins\.|Subs\.|Notification|Noti)\b)",
    re.M,
)
SECTION_RE = HEAD_RE   # kept for backwards compatibility
MAX_CHARS = 1600


def _major(num: str) -> int:
    return int(re.match(r"\d+", num).group(0))


def section_marks(text: str) -> list[tuple[int, str]]:
    """Candidate heads filtered to a plausible running sequence, so clause numbers like "(1)" or
    footnote digits are not mistaken for sections. A "Short title" head restarts numbering (Rules after
    an Act); a rejected head followed by two consecutive numbers re-synchronises the sequence (forward jumps only)."""
    cands = []
    for m in HEAD_RE.finditer(text):
        end = text.find("\n", m.start())
        cands.append((m.start(), m.group(1), _major(m.group(1)), text[m.start(): end if end != -1 else len(text)]))
    marks: list[tuple[int, str]] = []
    last: int | None = None
    for i, (pos, num, major, line) in enumerate(cands):
        if marks and num == marks[-1][1]:
            continue
        if re.search(r"\b(?:inserted|substituted|omitted|added|amended|renumbered)\s+(?:by|vide)\b", line, re.I):
            continue   # amendment footnote, not a head
        restart = major == 1 and re.search(r"short title|title and commencement", line, re.I)
        follows = last is not None and 0 <= major - last <= 3
        resync = (last is not None and major > last and i + 2 < len(cands)
                  and cands[i + 1][2] == major + 1 and cands[i + 2][2] == major + 2)
        # a head one below a suspicious jump (e.g. 5 -> 7 -> 6) means the jump was a stray number: replace it
        backfix = (last is not None and major == last - 1 and len(marks) >= 2 and last - _major(marks[-2][1]) >= 2)
        if backfix:
            marks[-1] = (pos, num)
            last = major
        elif last is None or restart or follows or resync:
            marks.append((pos, num))
            last = major
    return marks


def split_sections(text: str) -> list[tuple[str | None, str]]:
    text = FOOTNOTE_BRACKET.sub(r"\1", nfc(text))
    # Several source files repeat the full numbering in a contents table before
    # the actual instrument. Preserve that prefix as reference, not provisions.
    body_start = _body_start(text)
    prefix = text[:body_start] if body_start else ""
    text = text[body_start:]
    marks = section_marks(text)
    out: list[tuple[str | None, str]] = [(None, p) for p in _windows(prefix)]
    if not marks:
        return out + [(None, p) for p in _windows(text)]
    if marks[0][0] > 0:
        out += [(None, p) for p in _windows(text[: marks[0][0]])]
    for i, (pos, num) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        for part in _windows(text[pos:end].strip()):
            out.append((num, part))
    return out


def _body_start(text: str) -> int:
    for m in HEAD_RE.finditer(text):
        if m.group(1) == "1" and re.search(r"(?:this act|these rules).*?may be called", text[m.start():m.start() + 300], re.I | re.S):
            return m.start()
    return 0


@dataclass
class Provision:
    section: str | None
    text: str
    kind: str


def split_provisions(text: str, doc_type: str) -> list[Provision]:
    """Preserve instrument/appendix boundaries separately from numbered clauses.

    Unnumbered contents, schedules and annexures remain stored reference chunks;
    they are excluded from operational synthesis until explicitly modeled.
    """
    text = FOOTNOTE_BRACKET.sub(r"\1", nfc(text))
    default = {"rules": "rule", "manual": "paragraph"}.get(doc_type, "section")
    start = _body_start(text) if doc_type != "manual" else 0
    events = {0: "reference" if start else default}
    if start:
        events[start] = default
    for m in re.finditer(r"^\s*(?:\[?SCHEDULE(?:[- ]?[A-Z])?\]?|THE SCHEDULE|ANNEXURE\s+\w+|APPENDIX\s+\w+)\s*$", text, re.M | re.I):
        if m.start() >= start:
            events[m.start()] = "reference"
    for m in HEAD_RE.finditer(text):
        if m.start() < start or m.group(1) != "1":
            continue
        following = text[m.start():m.start() + 300]
        if re.search(r"these rules may be called", following, re.I):
            events[m.start()] = "rule"
        elif re.search(r"this act may be called.*?validation", following, re.I | re.S):
            # A second Act has a different identity; never cite it as the parent.
            events[m.start()] = "reference"
    parts = []
    positions = sorted(events)
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        kind = events[pos]
        body = text[pos:end]
        sections = [(None, p) for p in _windows(body)] if kind == "reference" else split_sections(body)
        for sec, chunk in sections:
            # PLRM's paragraph numbers are chapter-qualified; plain integer
            # lists/questions cannot inherit a paragraph citation.
            if kind == "paragraph" and "Land Records Manual" in text[:250] and sec and "." not in sec:
                sec = None
            parts.append(Provision(sec, chunk, kind if sec else "reference"))
    return parts


def _windows(s: str) -> list[str]:
    s = s.strip()
    if len(s) <= MAX_CHARS:
        return [s] if s else []
    parts, cur = [], ""
    for para in re.split(r"\n(?=\s*\(|\s*\n)", s):
        if len(cur) + len(para) > MAX_CHARS and cur:
            parts.append(cur.strip())
            cur = ""
        cur += para + "\n"
    if cur.strip():
        parts.append(cur.strip())
    final = []
    for p in parts:
        while len(p) > MAX_CHARS * 1.5:
            final.append(p[:MAX_CHARS])
            p = p[MAX_CHARS - 200:]
        final.append(p)
    return final


def ingest_laws(con: sqlite3.Connection, laws_dir: Path) -> dict:
    stats: dict = {"documents": 0, "chunks": 0, "skipped": []}
    mf = laws_dir / "manifest.json"
    if not mf.exists():
        stats["skipped"].append("no manifest.json")
        return stats
    manifest = json.loads(mf.read_text())
    for m in manifest:
        f = laws_dir / f"{m['slug']}.txt"
        if not f.exists() or f.stat().st_size < 500:
            stats["skipped"].append(m["slug"])
            continue
        text = f.read_text(errors="replace")
        row = con.execute("SELECT id FROM documents WHERE slug=?", (m["slug"],)).fetchone()
        cache: dict[str, tuple] = {}
        if row:
            doc_id = row[0]
            # keep vectors of unchanged passages so a re-ingest only embeds new text
            for r in con.execute("SELECT c.text, e.dim, e.vec, t.tokens FROM chunks c JOIN embeddings e ON e.chunk_id=c.id "
                                 "JOIN bm25_tokens t ON t.chunk_id=c.id WHERE c.doc_id=?", (doc_id,)):
                cache[r[0]] = (r[1], r[2], r[3])
            con.execute("DELETE FROM embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE doc_id=?)", (doc_id,))
            con.execute("DELETE FROM bm25_tokens WHERE chunk_id IN (SELECT id FROM chunks WHERE doc_id=?)", (doc_id,))
            con.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            con.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        doc_id = con.execute(
            "INSERT INTO documents(kind,slug,title,short_name,jurisdiction,doc_type,source_url,sha256,retrieved,complete,notes) "
            "VALUES ('law',?,?,?,?,?,?,?,?,?,?)",
            (m["slug"], m.get("title"), m.get("short_name"), m.get("jurisdiction"), m.get("kind"), m.get("source_url"),
             hashlib.sha256(text.encode()).hexdigest(), m.get("retrieved"), int(bool(m.get("complete", True))),
             " | ".join(x for x in (f"CAUTION: {m['version_note']}" if m.get("version_note") else None, m.get("notes")) if x) or None),
        ).lastrowid
        stats["documents"] += 1
        for i, part in enumerate(split_provisions(text, m.get("kind", "act"))):
            sec, body = part.section, part.text
            cid = hashlib.sha256(f"{m['slug']}|{i}|{body}".encode()).hexdigest()[:16]
            heading = body.splitlines()[0][:120] if body else None
            con.execute(
                "INSERT OR IGNORE INTO chunks(id,doc_id,ordinal,source_type,text,section,heading,quality_flags,excluded) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (cid, doc_id, i, "law", body, sec, heading,
                 f"structure_v2,provision_kind={part.kind}" + ("" if m.get("complete", True) else ",source_incomplete"),
                 int(part.kind == "reference")),
            )
            if body in cache:
                dim, vec, toks = cache[body]
                con.execute("INSERT OR IGNORE INTO embeddings VALUES (?,?,?)", (cid, dim, vec))
                con.execute("INSERT OR IGNORE INTO bm25_tokens VALUES (?,?)", (cid, toks))
                stats["reused_vectors"] = stats.get("reused_vectors", 0) + 1
            stats["chunks"] += 1
    con.commit()
    return stats
