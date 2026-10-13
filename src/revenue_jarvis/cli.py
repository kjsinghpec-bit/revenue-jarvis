"""`jarvis` command line: doctor, ocr, build, ask, chat, serve, eval."""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import db as dbm
from .config import get_settings

app = typer.Typer(add_completion=False, help="Revenue Jarvis - your page-cited Punjab revenue-law aide.")
console = Console()


@app.command()
def doctor():
    """Check everything Jarvis needs on this machine."""
    s = get_settings()
    t = Table(title="Revenue Jarvis - system check")
    t.add_column("Component"), t.add_column("Status"), t.add_column("Fix")
    ok = lambda b: "[green]OK[/]" if b else "[red]missing[/]"  # noqa: E731
    t.add_row("Knowledge base", ok(s.db_path.exists()), "jarvis build")
    t.add_row("Claude Code CLI", ok(shutil.which("claude")), "npm i -g @anthropic-ai/claude-code && claude (log in)")
    t.add_row("Codex CLI (fallback)", ok(shutil.which("codex")), "optional: npm i -g @openai/codex")
    t.add_row("ffmpeg (voice)", ok(shutil.which("ffmpeg")), "brew install ffmpeg")
    try:
        import mlx_whisper  # noqa: F401
        mlx = True
    except Exception:
        mlx = False
    t.add_row("MLX Whisper (voice)", ok(mlx), "pip install 'revenue-jarvis\\[voice]'")
    t.add_row("Book PDF (page images)", ok(bool(s.book_pdf and Path(s.book_pdf).exists())), "export JARVIS_BOOK_PDF=~/path/to/book.pdf")
    t.add_row("Tesseract (only to re-OCR)", ok(shutil.which("tesseract")), "brew install tesseract tesseract-lang")
    console.print(t)
    if s.db_path.exists():
        con = dbm.connect(s.db_path, readonly=True)
        h = dbm.health(con)
        console.print(h)
        if h["integrity"] != "ok":
            console.print("[red]Database is damaged: restore data/jarvis.db from the zip.[/]")
        elif h["chunks_without_vector"]:
            console.print(f"[yellow]Index is stale: {h['chunks_without_vector']} passages not searchable. Run: jarvis build[/]")


@app.command()
def ocr(pdf: Path = typer.Option(..., exists=True), tessdata: Path | None = None):
    """(Optional) Re-OCR the book locally. Resumable. Takes ~30-60 min on an M1."""
    s = get_settings()
    script = Path(__file__).resolve().parents[2] / "scripts" / "ocr_book.py"
    cmd = [sys.executable, str(script), "--pdf", str(pdf), "--out", str(s.data_dir / "book" / "ocr")]
    if tessdata:
        cmd += ["--tessdata", str(tessdata)]
    raise typer.Exit(subprocess.call(cmd))


@app.command()
def build(rebuild: bool = typer.Option(False, help="Delete and rebuild the knowledge base from OCR + law texts")):
    """Build the SQLite knowledge base: pages, chunks, law sections, vectors."""
    from .index import build_index
    from .ingest.book import ingest_book
    from .ingest.laws import ingest_laws

    s = get_settings()
    if rebuild and s.db_path.exists():
        s.db_path.unlink()
    con = dbm.connect(s.db_path)
    sha = None
    if s.book_pdf and Path(s.book_pdf).exists():
        sha = hashlib.sha256(Path(s.book_pdf).read_bytes()).hexdigest()
    console.print("[cyan]Loading book OCR...[/]", ingest_book(con, s.data_dir / "book" / "ocr", sha))
    console.print("[cyan]Loading acts & rules...[/]", ingest_laws(con, s.data_dir / "laws"))
    console.print("[cyan]Embedding (first run downloads the E5 model, ~470 MB)...[/]")
    console.print(build_index(con, s.embed_model, s.embed_revision, progress=lambda a, b: console.print(f"  {a}/{b}", end="\r")))
    con.close()


def _jarvis():
    from .answer import Jarvis

    s = get_settings()
    if not s.db_path.exists():
        console.print("[red]No knowledge base. Run: jarvis build[/]")
        raise typer.Exit(2)
    return Jarvis(s, dbm.connect(s.db_path))


@app.command()
def ask(question: str, json_out: bool = typer.Option(False, "--json")):
    """Ask one question and print a cited answer."""
    import json

    from .answer import render_text

    a = _jarvis().ask(question)
    if json_out:
        print(json.dumps(a.to_dict(), ensure_ascii=False, indent=2))
    else:
        console.print(Panel(render_text(a), title=f"JARVIS · {a.status} · {a.backend}", border_style="cyan"))
    raise typer.Exit(0 if a.status in ("answered", "need_facts") else 3)


@app.command()
def chat():
    """Terminal conversation with Jarvis (type 'exit' to leave)."""
    from .answer import render_text

    j = _jarvis()
    console.print(Panel(f"Good day, {j.s.user_title}. Engine: {j.backend.name if j.backend else 'sources-only'}.", border_style="cyan"))
    while True:
        try:
            q = console.input("[bold cyan]you ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit", "bye"):
            break
        if q:
            console.print(Panel(render_text(j.ask(q)), border_style="cyan"))


@app.command()
def serve(open_browser: bool = True, port: int | None = None):
    """Start the Jarvis interface at http://127.0.0.1:8765"""
    import uvicorn

    from .server import create_app

    s = get_settings()
    p = port or s.port
    if open_browser:
        webbrowser.open(f"http://{s.host}:{p}")
    uvicorn.run(create_app(s), host=s.host, port=p, log_level="warning")


@app.command("eval")
def evaluate(gold: Path = typer.Option(None, help="CSV of gold questions"), out: Path = typer.Option(Path("evaluation.csv"))):
    """Run the retrieval benchmark (recall@5 page hits) and write evaluation.csv."""
    from .evaluate import run_eval

    s = get_settings()
    gold = gold or (s.data_dir.parent / "tests" / "gold.csv")
    res = run_eval(s, gold, out)
    console.print(res["summary"])


if __name__ == "__main__":
    app()
