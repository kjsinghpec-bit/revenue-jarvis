"""Retrieval benchmark: question-level page hit in the top-5 unique book results (recall@5).

This measures whether the right page reaches the evidence set. It is NOT answer accuracy;
answers must still be reviewed against the scanned page before office use.
"""
from __future__ import annotations

import csv
import math
import time
import uuid
from pathlib import Path

import numpy as np

from . import db as dbm
from .config import Settings
from .index import encode_query
from .retrieve import Retriever
from .text import alias_terms, tokenize


def _pages(s: str) -> set[int]:
    out: set[int] = set()
    for part in str(s).replace(",", ";").split(";"):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out |= set(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def _single_mode_pages(r: Retriever, q: str, mode: str, k: int = 5) -> list[int]:
    pool = r.pools["book"]
    if mode == "dense":
        order = np.argsort(-(pool.vecs @ encode_query(r.model, q)))
    else:
        sc = pool.bm25.get_scores(tokenize(q + " " + " ".join(alias_terms(q))))
        order = [i for i in np.argsort(-sc) if sc[i] > 0]
    pages: list[int] = []
    for i in order:
        p = pool.meta[int(i)]["pdf_page_start"]
        if p not in pages:
            pages.append(p)
        if len(pages) == k:
            break
    return pages


def run_eval(s: Settings, gold_csv: Path, out_csv: Path) -> dict:
    con = dbm.connect(s.db_path)
    r = Retriever(con, s.embed_model, s.embed_revision, s.rrf_k, s.candidate_depth)
    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    rows = list(csv.DictReader(gold_csv.open(encoding="utf-8")))
    results = []
    for g in rows:
        t0 = time.time()
        evs = r.search(g["question"], None, top_book=5, top_law=3)
        lat = int((time.time() - t0) * 1000)
        gold = _pages(g["gold_pages"])
        got = [e.pdf_page for e in evs if e.source_type == "book"]
        laws = [e.citation for e in evs if e.source_type == "law"]
        hit = int(bool(gold & set(got)))
        d_hit = int(bool(gold & set(_single_mode_pages(r, g["question"], "dense"))))
        b_hit = int(bool(gold & set(_single_mode_pages(r, g["question"], "bm25"))))
        law_hit = ""
        if g.get("law_gold"):
            want = {(a.split(":")[0].strip(), sec.strip()) for a in g["law_gold"].split("|") for sec in a.split(":")[1].split(",")}
            law_hit = int(any((e.short_name, e.section) in want for e in evs if e.source_type == "law"))
        bucket = "" if hit else ("retrieval" if (d_hit or b_hit) else "retrieval_or_ocr")
        res = {**g, "retrieved_pages": ";".join(map(str, got)), "law_evidence": " | ".join(laws), "hit_at_5": hit, "law_hit_at_3": law_hit,
               "dense_only_hit": d_hit, "bm25_only_hit": b_hit, "latency_ms": lat, "error_bucket": bucket}
        results.append(res)
        con.execute("INSERT INTO eval_results(run_id,question_id,language,question,gold_pages,retrieved_pages,hit_at_5,latency_ms,error_bucket) "
                    "VALUES (?,?,?,?,?,?,?,?,?)", (run_id, g["question_id"], g["language"], g["question"], g["gold_pages"],
                                                   res["retrieved_pages"], hit, lat, bucket))
    con.commit()
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    n = len(results)
    hits = sum(x["hit_at_5"] for x in results)
    by_lang: dict[str, list[int]] = {}
    for x in results:
        by_lang.setdefault(x["language"], []).append(x["hit_at_5"])
    summary = {
        "run_id": run_id, "questions": n, "hits_at_5": hits, "recall_at_5": round(hits / n, 3) if n else 0,
        "dense_only": sum(x["dense_only_hit"] for x in results), "bm25_only": sum(x["bm25_only_hit"] for x in results),
        "law_hits_at_3": f"{sum(1 for x in results if x['law_hit_at_3'] == 1)}/{sum(1 for x in results if x['law_hit_at_3'] != '')}",
        "by_language": {k: f"{sum(v)}/{len(v)}" for k, v in by_lang.items()},
        "accepted_threshold": "15/20", "passes": hits >= math.ceil(0.75 * n),
    }
    return {"summary": summary, "results": results}
