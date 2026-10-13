"""Collect live HTTP timing/answers, or assess results with bound human audits.

python scripts/run_release_gates.py --collect --url http://127.0.0.1:8765
python scripts/run_release_gates.py --results reports/live_release.jsonl
Exit 0 only when every gate passes; absent/unreviewed evidence exits 1.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from revenue_jarvis.release import answer_hash, assess_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--questions", type=Path, default=ROOT / "tests" / "release_questions.json")
    parser.add_argument("--results", type=Path, default=ROOT / "reports" / "live_release.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "release_gates.json")
    args = parser.parse_args()
    if args.collect:
        questions = json.loads(args.questions.read_text())
        if not questions:
            parser.error("Question set is empty")
        args.results.parent.mkdir(parents=True, exist_ok=True)
        # Never append distinct runs together to manufacture enough samples.
        with args.results.open("w", encoding="utf-8") as stream:
            for i in range(50):
                q = questions[i % len(questions)]
                started = time.perf_counter()
                req = Request(args.url.rstrip("/") + "/api/ask", data=json.dumps({"question": q["question"]}).encode(), headers={"Content-Type": "application/json"})
                try:
                    with urlopen(req, timeout=220) as response:
                        answer = json.load(response)
                except OSError as error:
                    raise SystemExit(f"Live collection stopped: {type(error).__name__}. No release certification.") from error
                record = {"mode": "live", "question_id": q["question_id"], "elapsed_ms": (time.perf_counter() - started) * 1000,
                          "answer": answer, "answer_sha256": answer_hash(answer)}
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                print(f"{i + 1}/50 {q['question_id']} {answer['status']} {record['elapsed_ms']:.0f} ms", flush=True)
    records = [json.loads(line) for line in args.results.read_text().splitlines() if line.strip()] if args.results.exists() else []
    gates = assess_release(records)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"gates": gates, "release_approved": all(g["status"] == "pass" for g in gates)}, indent=2))
    print(json.dumps(gates, indent=2))
    return 0 if all(g["status"] == "pass" for g in gates) else 1


if __name__ == "__main__":
    raise SystemExit(main())
