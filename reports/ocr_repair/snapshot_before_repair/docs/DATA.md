# Data model (`data/jarvis.db`)

One SQLite file holds every piece of state. Open it with any SQLite browser.

| Table | One row per | Key columns |
|---|---|---|
| `meta` | setting | `schema_version`, `embed_model`, `embed_revision` |
| `documents` | source (the book, each act/rules/manual) | `kind` book/law, `short_name`, `jurisdiction`, `source_url`, `sha256`, `retrieved`, `complete`, `notes` (version caveats) |
| `pages` | scanned book page | `pdf_page`, `printed_label` (only when OCR-verified), `label_source`, `text_raw`, `text_clean`, `n_lines`, `failed_lines`, `recovered_lines` (psm 13 rescues), `quality` ok/partial/empty, `is_front_matter`, `image_sha256` |
| `chunks` | searchable passage | `source_type` book/law, `text`, `pdf_page_start`, `printed_labels`, `section`, `heading`, `quality_flags`, `excluded` (contents pages) |
| `embeddings` | chunk vector | 384-dim float32 `vec` (multilingual-e5-small, normalised) |
| `bm25_tokens` | chunk token list | JSON list used to build BM25 at start-up |
| `qa_log` | question asked | `question`, `language`, `backend`, `status`, `answer_json`, `evidence_ids`, `latency_ms` |
| `eval_results` | benchmark row | `run_id`, `question_id`, `gold_pages`, `retrieved_pages`, `hit_at_5`, `error_bucket` |

## Provenance rules

* Book page images are never stored; they're rendered on demand from your own PDF (`JARVIS_BOOK_PDF`).
* `printed_label` is filled only when the number on the page agrees with the book's observed offset (printed = PDF − 15). Otherwise it stays empty and citations show the PDF page only.
* Each law file records the official URL and, in `notes`, the archive snapshot date and any version caveat (for example, the Consolidation text is the Haryana-applicable version and the Stamp Act text is current only to about 2001).
* Raw OCR (`text_raw`) is kept beside the cleaned text; the cleaner only normalises Unicode, spacing and pure-noise lines and never changes words.

## Useful queries

```sql
-- pages with OCR problems
SELECT pdf_page, quality, failed_lines, recovered_lines FROM pages WHERE quality <> 'ok' OR recovered_lines > 10;
-- what Jarvis was asked this week
SELECT ts, question, status, backend FROM qa_log WHERE ts > datetime('now','-7 days') ORDER BY ts DESC;
-- integrity
PRAGMA integrity_check;
SELECT COUNT(*) FROM chunks WHERE id NOT IN (SELECT chunk_id FROM embeddings);  -- must be 0
```
