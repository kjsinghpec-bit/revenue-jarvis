"""Hybrid retrieval: E5 dense + BM25 sparse, fused with Reciprocal Rank Fusion.

The book (primary) and the laws (secondary) are ranked as two separate pools so
statutes can never crowd the book out of the evidence.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

from .index import encode_query, load_encoder
from .ocr_review import page_review
from .text import GURMUKHI, alias_terms, detect_language, english_terms, tokenize
from .xref import extract_citations

# Reciprocal-rank-fusion weights. A section the book itself cites is the strongest signal for the law pool.
WEIGHTS = {"dense": 1.0, "bm25": 1.0, "xref": 3.0}


@dataclass
class Evidence:
    sid: str                 # "B1".."B5" (book) or "L1".."L3" (law)
    chunk_id: str
    source_type: str
    text: str
    doc_title: str
    short_name: str | None
    pdf_page: int | None = None
    printed_page: str | None = None
    section: str | None = None
    source_url: str | None = None
    score: float = 0.0
    ranks: dict = field(default_factory=dict)
    neighbors: str = ""
    source_note: str | None = None      # version / completeness caveat for a law text
    provision_kind: str | None = None
    locator_verified: bool = True
    ocr_status: str | None = None
    scan_verified: bool = False

    @property
    def citation(self) -> str:
        if self.source_type == "book":
            book = f"Book p.{self.printed_page}; " if self.printed_page else ""
            return f"[Bhumbak, {book}PDF p.{self.pdf_page}]"
        name = self.short_name or self.doc_title
        if not self.section:
            return f"[{name}]"
        unit = {"paragraph": "para", "rule": "r.", "section": "s."}.get(self.provision_kind)
        unit = unit or ("para" if name.startswith(("PLRM", "PLAM")) else ("r." if "Rules" in name and "Act" not in name else "s."))
        sep = " " if unit == "para" else ""
        return f"[{unit}{sep}{self.section}, {name}]"


def _caution(m: dict) -> str | None:
    """Version / completeness caution recorded for a law text, shown beside any answer that cites it."""
    notes = m.get("notes") or ""
    caution = next((p.strip()[len("CAUTION:"):].strip() for p in notes.split(" | ") if p.strip().startswith("CAUTION:")), None)
    if caution:
        return caution
    return None if m.get("complete", 1) else (notes or "source text may be incomplete")


class Pool:
    def __init__(self, ids, texts, vecs, tokens, meta):
        self.ids, self.texts, self.vecs, self.meta = ids, texts, vecs, meta
        self.bm25 = BM25Okapi(tokens) if tokens else None
        self.index = {cid: i for i, cid in enumerate(ids)}


class Retriever:
    def __init__(self, con: sqlite3.Connection, model_name: str, revision: str = "main", rrf_k: int = 60, depth: int = 30):
        self.con, self.rrf_k, self.depth = con, rrf_k, depth
        self.model_name, self.revision = model_name, revision
        self.last_timings: dict[str, float] = {}
        self.pools = {st: self._load(st) for st in ("book", "law")}

    def _load(self, source_type: str) -> Pool:
        rows = self.con.execute(
            "SELECT c.id, c.doc_id, c.text, c.pdf_page_start, c.printed_labels, c.section, c.quality_flags, d.title, d.short_name, d.source_url, d.complete, d.notes, "
            "e.vec, t.tokens FROM chunks c JOIN documents d ON d.id=c.doc_id JOIN embeddings e ON e.chunk_id=c.id "
            "JOIN bm25_tokens t ON t.chunk_id=c.id WHERE c.source_type=? AND c.excluded=0 ORDER BY c.id",
            (source_type,),
        ).fetchall()
        if not rows:
            return Pool([], [], np.zeros((0, 384), np.float32), [], [])
        vecs = np.vstack([np.frombuffer(r["vec"], dtype=np.float32) for r in rows])
        meta = [dict(r) for r in rows]
        if source_type == "law":
            for m in meta:
                if "structure_v2" not in (m.get("quality_flags") or "").split(","):
                    m["section"] = None
                    m["notes"] = "CAUTION: Unverified provision boundaries; law rebuild required. | " + (m.get("notes") or "")
        return Pool([r["id"] for r in rows], [r["text"] for r in rows], vecs,
                    [json.loads(r["tokens"]) for r in rows], meta)

    @property
    def model(self):
        return load_encoder(self.model_name, self.revision)

    def _rank(self, pool: Pool, qv: np.ndarray, qtok: list[str], xref: list[int] | None = None) -> list[tuple[str, float, dict]]:
        if not pool.ids:
            return []
        depth = min(self.depth, len(pool.ids))
        dense = np.argsort(-(pool.vecs @ qv))[:depth]
        ranks: dict[int, dict] = {}
        for r, i in enumerate(dense, 1):
            ranks.setdefault(int(i), {})["dense"] = r
        if pool.bm25 is not None and qtok:
            sc = pool.bm25.get_scores(qtok)
            order = [int(i) for i in np.argsort(-sc)[:depth] if sc[i] > 0]   # drop zero-score lexical matches
            for r, i in enumerate(order, 1):
                ranks.setdefault(i, {})["bm25"] = r
        for r, i in enumerate(xref or [], 1):          # sections the book itself cites
            ranks.setdefault(i, {})["xref"] = r
        fused = [(pool.ids[i], sum(WEIGHTS[src] / (self.rrf_k + rk) for src, rk in d.items()), d) for i, d in ranks.items()]
        fused.sort(key=lambda x: (-x[1], x[0]))     # stable tie-break on chunk id
        return fused

    def search(self, question: str, extra_terms: list[str] | None = None, top_book: int = 5, top_law: int = 3) -> list[Evidence]:
        q = question.strip()
        started = time.perf_counter()
        self.last_timings = {}
        lang = detect_language(q)
        bridge = alias_terms(q) if lang != "hi" else []  # Skip book search prep if Hindi
        english = english_terms(q)
        extra = list(dict.fromkeys(str(t)[:80] for t in (extra_terms or [])[:10]))
        qv = encode_query(self.model, (q + " " + " ".join(bridge + english + extra)).strip())
        self.last_timings["encode_query"] = (time.perf_counter() - started) * 1000
        # Book is Gurmukhi: when bridge terms exist, English words only add noise from the book's few English pages.
        native = [t for t in tokenize(q) if GURMUKHI.search(t) or t.isdecimal()]
        tok_book = native + tokenize(" ".join(bridge)) if bridge else tokenize(q)
        tok_book += tokenize(" ".join(extra))
        tok_law = tokenize(q + " " + " ".join(bridge + english + extra))
        out: list[Evidence] = []
        cites = extract_citations(q)
        # Search book only if question is in Gurmukhi or English (not Hindi/Devanagari)
        for st, k, prefix, qtok in ((("book", top_book, "B", tok_book),) if lang != "hi" else ()) + (("law", top_law, "L", tok_law),):
            pool = self.pools[st]
            started = time.perf_counter()
            xref = self._xref_indices(pool, cites) if st == "law" else None
            seen: set = set()
            n = 0
            for cid, score, rk in self._rank(pool, qv, qtok, xref):
                m = pool.meta[pool.index[cid]]
                key = m["pdf_page_start"] if st == "book" else (m["short_name"], m["section"] or m["text"][:80])
                if key in seen:
                    continue
                seen.add(key)
                n += 1
                out.append(Evidence(f"{prefix}{n}", cid, st, m["text"], m["title"], m["short_name"], m["pdf_page_start"],
                                    m["printed_labels"], m["section"], m["source_url"], round(score, 5), rk,
                                    source_note=_caution(m) if st == "law" else None,
                                    provision_kind=_provision_kind(m),
                                    locator_verified=st != "law" or "structure_v2" in (m.get("quality_flags") or "").split(","),
                                    **(page_review(self.con, m['doc_id'], m['pdf_page_start'], m['text']) if st == 'book' else {})))
                if st == "book":
                    cites += [c for c in extract_citations(m["text"]) if c not in cites]
                if n >= k:
                    break
            self.last_timings[f"rank_{st}"] = (time.perf_counter() - started) * 1000
        return out

    @staticmethod
    def _xref_indices(pool: Pool, cites: list[tuple[str, str]]) -> list[int]:
        """Law chunks whose (act, section) the question or the retrieved book pages cite, in citation order."""
        out: list[int] = []
        for act, sec in cites:
            for i, m in enumerate(pool.meta):
                name = m["short_name"] or ""
                act_ok = name == act or (act == "PLRM" and name == f"PLRM Ch {sec.split('.')[0]}")
                if act_ok and m["section"] == sec and i not in out:
                    out.append(i)
        return out

    def neighbors(self, ev: Evidence, chars: int = 450) -> str:
        """Bounded text from the next page / next section: exceptions often continue there."""
        row = self.con.execute("SELECT doc_id, ordinal FROM chunks WHERE id=?", (ev.chunk_id,)).fetchone()
        if not row:
            return ""
        nxt = self.con.execute("SELECT text FROM chunks WHERE doc_id=? AND ordinal>? AND excluded=0 ORDER BY ordinal LIMIT 1",
                               (row["doc_id"], row["ordinal"])).fetchone()
        return nxt["text"][:chars] if nxt else ""

    def neighbor_evidence(self, ev: Evidence, sid: str, chars: int = 450) -> Evidence | None:
        """Adjacent context has its own identity and locator; never inherit the parent citation."""
        row = self.con.execute("SELECT doc_id, ordinal FROM chunks WHERE id=?", (ev.chunk_id,)).fetchone()
        if not row:
            return None
        nxt = self.con.execute(
            "SELECT c.*, d.title, d.short_name, d.source_url, d.complete, d.notes FROM chunks c "
            "JOIN documents d ON d.id=c.doc_id WHERE c.doc_id=? AND c.ordinal>? AND c.excluded=0 ORDER BY c.ordinal LIMIT 1",
            (row["doc_id"], row["ordinal"]),
        ).fetchone()
        if not nxt:
            return None
        verified = nxt["source_type"] != "law" or "structure_v2" in (nxt["quality_flags"] or "").split(",")
        return Evidence(sid, nxt["id"], nxt["source_type"], nxt["text"][:chars], nxt["title"], nxt["short_name"],
                        nxt["pdf_page_start"], nxt["printed_labels"], nxt["section"] if verified else None, nxt["source_url"],
                        source_note=_caution(dict(nxt)) if ev.source_type == "law" else None,
                        provision_kind=_provision_kind(dict(nxt)), locator_verified=verified,
                        **(page_review(self.con, nxt['doc_id'], nxt['pdf_page_start'], nxt['text'][:chars]) if nxt['source_type'] == 'book' else {}))


def _provision_kind(meta: dict) -> str | None:
    flags = (meta.get("quality_flags") or "").split(",")
    return next((x.split("=", 1)[1] for x in flags if x.startswith("provision_kind=")), None)
