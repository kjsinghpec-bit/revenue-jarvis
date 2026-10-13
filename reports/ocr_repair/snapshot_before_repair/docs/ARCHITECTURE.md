# Architecture

![How Revenue Jarvis answers](architecture.png)

```mermaid
flowchart LR
  subgraph Mac["Your M1 Mac (127.0.0.1 only)"]
    UI["Jarvis HUD<br/>browser: orb, transcript,<br/>evidence cards"]
    API["FastAPI server<br/>/api/ask /transcribe /tts /page"]
    STT["MLX Whisper<br/>(speech to text)"]
    RET["Hybrid retriever<br/>E5 dense + BM25 → RRF<br/>book pool | law pool"]
    VAL["Citation validator<br/>schema + id check"]
    DB[("jarvis.db (SQLite)<br/>documents · pages · chunks<br/>embeddings · bm25_tokens<br/>qa_log · eval_results")]
    CLI["claude -p  /  codex exec<br/>(tools disabled)"]
  end
  SUB["Your Claude / ChatGPT<br/>subscription"]
  TTS["edge-tts neural voice<br/>(free, internet)"]

  UI -- voice --> API --> STT
  UI -- question --> API --> RET --> DB
  RET -- B1..B5, L1..L3 --> CLI --> SUB
  CLI --> VAL --> API --> UI
  API -- spoken text --> TTS --> UI
  API --> DB
```

## Offline build pipeline (already run; repeat only to rebuild)

```mermaid
flowchart TB
  PDF["Book PDF (389 scanned pages)"] --> R["Render 300 dpi grey"]
  R --> RR["Remove table rulings"]
  RR --> SEG["Ink-profile line segmentation"]
  SEG --> OCR["Tesseract pan+eng per line<br/>psm 7, scale retries, psm 13 rescue"]
  OCR --> J["page_NNNN.json<br/>(text, lines, failures, hashes)"]
  J --> ING["ingest: clean, verify printed page,<br/>exclude front matter, ~700-char chunks"]
  LAWS["27 official acts / rules / manuals<br/>(Punjab Revenue Dept, India Code)"] --> SEC["split by section number"]
  ING --> DB[("jarvis.db")]
  SEC --> DB
  DB --> EMB["multilingual-e5-small vectors + BM25 tokens"] --> DB
```

## Modules (`src/revenue_jarvis/`)

| Module | Job |
|---|---|
| `config.py` | Pydantic settings (`JARVIS_*` env vars / `.env`) |
| `ocr/engine.py` | Line-segmenting Tesseract OCR with explicit failure flags |
| `ingest/book.py` | OCR JSON → `pages` + page-linked `chunks`; printed page only when OCR-verified |
| `ingest/laws.py` | Bare acts → section-level `chunks` with source URL and hash |
| `index.py` | E5 embeddings and BM25 tokens stored in SQLite |
| `retrieve.py` | Hybrid search, RRF, separate book/law pools, neighbour context |
| `llm.py` | Claude Code / Codex subprocess backends; strips API-key env vars so only the subscription login is used |
| `answer.py` | Prompt, JSON schema, citation validation, sources-only fallback, Q&A log |
| `voice.py` | MLX Whisper / faster-whisper STT; edge-tts TTS |
| `server.py` | Local web API + static HUD |
| `cli.py` | `jarvis doctor / ocr / build / ask / chat / serve / eval` |
| `evaluate.py` | Recall@5 benchmark with dense-only and BM25-only diagnostics |

## Design decisions

* **Book first, structurally.** Book and law are ranked in separate pools and labelled B/L; the prompt and the validator both treat B ids as primary. A statute can add or conflict, never silently replace.
* **No model-written page numbers.** Citations are rendered from stored metadata, so a model can't invent a page or section.
* **Fail closed.** Bad JSON, an unknown citation id, a timeout or a missing CLI all lead to sources-only, never an unverified answer.
* **One file of state.** All data lives in `data/jarvis.db`; back it up by copying one file.
* **No API billing.** The Claude/Codex subprocesses run with `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` removed from their environment.
