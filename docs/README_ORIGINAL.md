# Revenue Jarvis

> *"Good evening, sir. Your revenue library is ready."*

Revenue Jarvis is a private, voice-first aide for Punjab revenue work. You ask in **English, ਪੰਜਾਬੀ, हिन्दी or a mix**, by voice or text. Jarvis searches **Sohan Lal Bhumbak's *Zameen Di Guide*** first (primary source) and **27 official acts, rules and manuals** second (supporting source). It answers in your language with a page citation on every point, like `[Bhumbak, Book p.152; PDF p.167]` or `[s.111, PLRA 1887]`.

Everything runs on your Mac and costs nothing extra:

| Part | What it uses | Cost |
|---|---|---|
| Book text | Local Tesseract OCR (pan+eng), already done: all 389 pages | free |
| Search | Multilingual E5 vectors + BM25 keywords, fused by RRF, in one SQLite file | free, offline |
| Thinking | **Claude Code** (`claude -p`) with tools and customizations disabled | your existing plan, no API key |
| Voice in | MLX Whisper on the M1 (local) or the browser's recogniser | free |
| Voice out | Free neural voices (edge-tts: British "Ryan", Hindi, Punjabi), Mac system voice when offline | free |

Without an available authenticated Claude engine, Jarvis works in **sources-only** mode. Codex synthesis is withheld until a tool-free transport is available. See [grounding repairs and release verification](docs/GROUNDING_FIXES.md) for the repaired database, test results and pending live production gates.

## Quick start (M1 MacBook, 8 GB)

```bash
unzip revenue-jarvis.zip && cd revenue-jarvis
./scripts/setup_mac.sh          # venv, packages, embedding model, ffmpeg
source .venv/bin/activate
jarvis doctor                   # checks Claude Code, voice, knowledge base
jarvis serve                    # opens http://127.0.0.1:8765
```

Hold **Space** (or the mic button) to talk, release to send. Press **Esc** to stop Jarvis speaking. Click any citation chip or evidence card to open the source; if you set `JARVIS_BOOK_PDF` in `.env` to your copy of the book, the original scanned page shows beside the OCR text.

Terminal users:

```bash
jarvis ask "Who may apply for partition and before whom?"
jarvis chat
jarvis eval          # re-runs the 20-question benchmark -> evaluation.csv
```

## How an answer is built

1. Your question's language is detected (pa / hi / en / hinglish).
2. Search terms are widened with a reviewed glossary (partition → ਤਕਸੀਮ, consolidation → ਮੁਰੱਬੇਬੰਦੀ, shamlat → ਸ਼ਾਮਲਾਤ …). LLM keyword rewrite is disabled by default; opt-in terms are included in retrieval.
3. Book and law are searched as **separate pools**: top 5 book passages (B1–B5) and top 3 statute passages (L1–L3), so the acts can never crowd the book out.
4. One call to Claude Code with strict rules: book first when available, law-only synthesis for Hindi input, source-specific supporting quotes, and differences under "Act vs Book". Replies use English or Gurmukhi.
5. Code checks supporting quotes, amounts/units, instruction patterns and locators; unsupported output is withheld. Neighboring chunks keep separate citations. Speech is assembled from surviving claims, and each answer's citation buttons retain its own evidence. These checks require a source/translation audit before production certification.
6. The question, evidence ids and answer are logged in the same SQLite file.

## Important limits

* Answers state the **book's position** with official text for support. Current amendments are **not** independently verified; check the latest notification before an order.
* The book is a scanned Gurmukhi text read by OCR. It's good but not perfect: 2 pages (a map and a sideways sample form) have no text, and 65 body pages have no verified printed page number. Always open the cited page before relying on a point.
* The book is copyrighted. This package contains the OCR text only for your private use; don't publish the database or the repository.

![How Revenue Jarvis answers](docs/architecture.png)

See `docs/` for the architecture, user guide, data model and test report.
