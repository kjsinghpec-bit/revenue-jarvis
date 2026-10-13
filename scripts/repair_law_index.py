"""Stage a law re-ingestion using the already cached E5 weights, then verify it.

This does not activate the staged DB. It compares direct HF mean pooling with
stored vectors before reusing any, and records the actual model revision.
Requires torch/transformers/numpy; no model downloads or legal data collection.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from revenue_jarvis import db, index, retrieve
from revenue_jarvis.ingest.laws import ingest_laws


class CachedE5:
    def __init__(self):
        torch.set_num_threads(2)
        self.path = Path.home() / ".cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots"
        snapshots = [p for p in self.path.iterdir() if (p / "model.safetensors").exists()]
        if len(snapshots) != 1:
            raise RuntimeError("Select an unambiguous cached E5 snapshot first")
        self.path = snapshots[0]
        pool = json.loads((self.path / "1_Pooling/config.json").read_text())
        if not pool.get("pooling_mode_mean_tokens") or pool.get("pooling_mode_cls_token") or pool.get("pooling_mode_max_tokens"):
            raise RuntimeError("Cached pooling configuration differs from mean pooling")
        self.tokenizer = AutoTokenizer.from_pretrained(self.path, local_files_only=True)
        self.model = AutoModel.from_pretrained(self.path, local_files_only=True).eval()

    def encode(self, texts, **kwargs):
        batches = []
        for start in range(0, len(texts), 8):
            tokens = self.tokenizer(texts[start:start + 8], padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.inference_mode():
                hidden = self.model(**tokens).last_hidden_state
                mask = tokens["attention_mask"]
                hidden = hidden.masked_fill(~mask[..., None].bool(), 0.0)
                vectors = hidden.sum(dim=1) / mask.sum(dim=1)[..., None]
                vectors = torch.nn.functional.normalize(vectors, p=2, dim=1)
            batches.append(vectors.numpy().astype(np.float32))
        return np.vstack(batches)


def main():
    out = ROOT / "reports/grounding_fixes"
    out.mkdir(parents=True, exist_ok=True)
    model = CachedE5()
    source = db.connect(ROOT / "data/jarvis.db", readonly=True)
    sample = source.execute("SELECT c.text, d.short_name, e.vec FROM chunks c JOIN documents d ON c.doc_id=d.id JOIN embeddings e ON c.id=e.chunk_id ORDER BY c.id LIMIT 20").fetchall()
    texts = [(f"{r['short_name']}: " if r["short_name"] and r["short_name"] != "Bhumbak" else "") + r["text"] for r in sample]
    fresh = index.encode_passages(model, texts)
    similarity = [float(v @ np.frombuffer(r["vec"], dtype=np.float32)) for v, r in zip(fresh, sample, strict=True)]
    if min(similarity) < 0.9999:
        raise RuntimeError(f"Cached encoder does not match stored vectors: minimum cosine {min(similarity)}")
    staged = out / "jarvis.staged.db"
    if staged.exists():
        raise RuntimeError("A staged database already exists; inspect it before rerunning")
    con = db.connect(staged)
    source.backup(con)
    source.close()
    stats = ingest_laws(con, ROOT / "data/laws")
    index.load_encoder = lambda *args: model
    retrieve.load_encoder = lambda *args: model
    built = index.build_index(con, "intfloat/multilingual-e5-small", model.path.name,
                              progress=lambda n, total: print(f"Re-embedded {n}/{total}", flush=True))
    r = retrieve.Retriever(con, "intfloat/multilingual-e5-small", model.path.name)
    timings = []
    for question in ("Who may apply for partition?", "ਤਕਸੀਮ ਲਈ ਕੌਣ ਦਰਖ਼ਾਸਤ ਦੇ ਸਕਦਾ ਹੈ?", "बंटवारे के लिए कौन आवेदन कर सकता है?"):
        start = time.perf_counter()
        evs = r.search(question)
        timings.append({"question": question, "elapsed_ms": (time.perf_counter() - start) * 1000,
                        "stages": r.last_timings.copy(), "sources": [e.citation for e in evs]})
    report = {"model_revision": model.path.name, "encoder_adapter": "Hugging Face, cached E5 mean pooling, normalized",
              "comparison_samples": len(sample), "minimum_cosine": min(similarity), "ingestion": stats, "index": built,
              "health": db.health(con), "retrieval_samples": timings}
    (out / "index_repair.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    con.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
