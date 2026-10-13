"""Local web app (FastAPI). Binds to 127.0.0.1 only: nothing is exposed to the network."""
from __future__ import annotations

import threading
import time
import subprocess
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db as dbm
from .answer import Jarvis
from .config import Settings, get_settings
from .profiling import write_profile
from .ocr_review import page_review
from .page_scan import matching_scan, render_png
from .runtime import source_revision, corpus_revision
from .voice import STTUnavailable, transcribe, tts_mp3

WEB = Path(__file__).parent / "web"


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class TTSIn(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    lang: str = "en"


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or get_settings()
    if not s.db_path.exists():
        raise SystemExit(f"Knowledge base not found at {s.db_path}. Run: jarvis build")
    con = dbm.connect(s.db_path)
    loaded_code = source_revision()
    loaded_corpus = corpus_revision(con)
    def restart_required():
        return loaded_code != source_revision() or loaded_corpus != corpus_revision(con)
    book = con.execute("SELECT id,sha256 FROM documents WHERE kind='book' ORDER BY id LIMIT 1").fetchone()
    scan_path = s.book_pdf or (s.data_dir.parent / 'Punjabi book .pdf')
    def scan_available():
        return bool(book and matching_scan(scan_path, book['sha256']))
    lock = threading.RLock()
    state: dict = {}

    def jarvis() -> Jarvis:
        with lock:
            if "j" not in state:
                state["j"] = Jarvis(s, con)
            return state["j"]

    app = FastAPI(title="Revenue Jarvis", version="1.0.0")
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @app.get("/api/status")
    def status():
        q = lambda sql: con.execute(sql).fetchone()[0]  # noqa: E731
        backend = jarvis().backend
        return {
            "book_pages": q("SELECT COUNT(*) FROM pages"),
            "book_pages_indexed": q("SELECT COUNT(DISTINCT pdf_page_start) FROM chunks WHERE source_type='book' AND excluded=0"),
            "book_pages_empty": q("SELECT COUNT(*) FROM pages WHERE quality='empty'"),
            "book_pages_partial": q("SELECT COUNT(*) FROM pages WHERE quality='partial'"),
            "laws": [dict(r) for r in con.execute("SELECT short_name, title, jurisdiction, doc_type, complete FROM documents WHERE kind='law' ORDER BY jurisdiction DESC, short_name")],
            "chunks": q("SELECT COUNT(*) FROM chunks"),
            "backend": backend.name if backend else "sources-only",
            "stt_engine": s.stt_engine,
            "page_images": scan_available(),
            "book_pages_scan_verified": sum(page_review(con, r['doc_id'], r['pdf_page'])['scan_verified'] for r in con.execute('SELECT doc_id,pdf_page FROM pages WHERE is_front_matter=0').fetchall()),
            "title": s.user_title,
            "runtime_revision": loaded_code[:12],
            "corpus_revision": loaded_corpus[:12],
            "restart_required": restart_required(),
        }

    @app.post("/api/ask")
    def ask(body: AskIn):
        started = time.perf_counter()
        with lock:   # one question at a time: the subscription CLI is single-user
            acquired = time.perf_counter()
            if restart_required():
                raise HTTPException(503, 'Jarvis needs a restart to load the updated code or knowledge base. Your question has not been sent to Claude.')
            engine = jarvis()
            initialized = time.perf_counter()
            answer = engine.ask(body.question)
            answer.timings["queue_wait"] = (acquired - started) * 1000
            answer.timings["initialize"] = (initialized - acquired) * 1000
            answer.timings["request_total"] = (time.perf_counter() - started) * 1000
            try:
                write_profile(s.data_dir, "request", answer_id=answer.answer_id, backend=answer.backend, status=answer.status, timings=answer.timings)
            except OSError:
                answer.warnings.append("Request profile could not be saved.")
            return JSONResponse(answer.to_dict())

    @app.post("/api/transcribe")
    async def stt(audio: UploadFile = File(...)):
        data = await audio.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "audio too long")
        suffix = Path(audio.filename or "a.webm").suffix or ".webm"
        try:
            from starlette.concurrency import run_in_threadpool
            started = time.perf_counter()
            result = await run_in_threadpool(transcribe, data, suffix, s.stt_engine, s.whisper_model)
            result["timings"] = {"transcribe": (time.perf_counter() - started) * 1000}
            write_profile(s.data_dir, "voice_input", timings=result["timings"])
            return result
        except STTUnavailable as e:
            raise HTTPException(501, str(e)) from e

    @app.post("/api/tts")
    def tts(body: TTSIn):
        try:
            return Response(tts_mp3(body.text, body.lang), media_type="audio/mpeg")
        except Exception as e:  # network down / gTTS missing: the UI falls back to the system voice
            raise HTTPException(503, str(e)) from e

    @lru_cache(maxsize=64)
    def _page_png(n: int, file_mtime: int) -> bytes:
        try:
            return render_png(scan_path, n)
        except (OSError, ValueError, subprocess.SubprocessError):
            raise HTTPException(503, 'Original scan could not be rendered.')

    @app.get("/api/page/{n}.png")
    def page_image(n: int):
        if not scan_available():
            raise HTTPException(404, 'Original PDF unavailable or its checksum does not match the indexed book. Set JARVIS_BOOK_PDF to the original scan.')
        if not con.execute('SELECT 1 FROM pages WHERE doc_id=? AND pdf_page=?', (book['id'], n)).fetchone():
            raise HTTPException(404, 'no such page')
        return Response(_page_png(n, scan_path.stat().st_mtime_ns), media_type='image/png')

    @app.get("/api/page/{n}/text")
    def page_text(n: int):
        r = con.execute("SELECT doc_id, pdf_page, printed_label, text_clean, quality FROM pages WHERE pdf_page=?", (n,)).fetchone()
        if not r:
            raise HTTPException(404, "no such page")
        return {**dict(r), **page_review(con, r['doc_id'], n)}

    @app.get("/api/history")
    def history(limit: int = 20):
        rows = con.execute("SELECT id, ts, question, status, backend, latency_ms FROM qa_log ORDER BY id DESC LIMIT ?", (min(limit, 200),))
        return [dict(r) for r in rows]

    return app
