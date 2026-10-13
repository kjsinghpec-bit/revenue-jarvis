"""Stage measurements without logging prompts, questions, or credentials."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_lock = threading.Lock()


def write_profile(data_dir: Path, event: str, **fields) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    record = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}
    with _lock, (data_dir / "timings.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
