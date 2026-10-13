# User guide

## 1. First-time setup (about 15 minutes)

1. Install [Homebrew](https://brew.sh) if you don't have it.
2. Install Claude Code and log in once with your Claude subscription:
   `npm install -g @anthropic-ai/claude-code` then run `claude` and follow the login.
   (Optional fallback: `npm install -g @openai/codex` and `codex login`.)
3. In the project folder run `./scripts/setup_mac.sh`.
4. Optional: in `.env`, set `JARVIS_BOOK_PDF` to your own copy of the book so Jarvis can show the scanned page.
5. Run `jarvis doctor`. Green rows are ready; red rows show the fix.

## 2. Talking to Jarvis

`source .venv/bin/activate && jarvis serve` opens the interface.

* **Speak:** hold **Space** (or press and hold the mic), talk, release. The orb turns green while listening, amber while it reads the sources, and pulses blue while it speaks.
* **Type:** write in the bar and press Enter. Mixed language works ("partition da case kithe file hunda").
* **Stop speech:** Esc. Mute Jarvis with the 🔊 button.
* **Sources:** each point carries chips like `B2` (book) or `L1` (law). Click one to open the passage; the right-hand panel lists all evidence.
* **Recent questions** (left panel) can be clicked to ask again.

### What the answer sections mean

| Section | Meaning |
|---|---|
| FROM THE BOOK | Points taken from Bhumbak, each with its page |
| STATUTORY SUPPORT | What the act/rule adds, with section number |
| ACT vs BOOK | Where the official text says more or differs; read this before passing an order |
| FACTS I NEED | The answer depends on facts you didn't give |
| ⚠ lines | OCR caveats, suppressed claims, or the standing current-law warning |

Status `sources_only` means Jarvis couldn't produce a verified answer (no engine, timeout, or a failed citation check), so it shows the pages to read instead.

## 3. Good questions to try

* Who may apply for partition and what happens if a question of title is raised?
* ਮੁਰੱਬੇਬੰਦੀ ਵੇਲੇ ਸਕੂਲ ਅਤੇ ਸ਼ਮਸ਼ਾਨਘਾਟ ਲਈ ਕਿੰਨੀ ਜ਼ਮੀਨ ਰਾਖਵੀਂ ਰੱਖੀ ਜਾਂਦੀ ਹੈ?
* शामलात ज़मीन से नाजायज़ कब्ज़ा हटाने के लिए पंचायत कहाँ आवेदन करती है?
* How does the district price fixation committee fix the price when a department buys land directly?
* When may a duplicate (musanna) of a lost mutation be prepared?

## 4. Settings (`.env`)

| Variable | Default | Use |
|---|---|---|
| `JARVIS_LLM_BACKEND` | `auto` | `claude`, `codex`, or `none` (sources only) |
| `JARVIS_CLAUDE_MODEL` | your default | e.g. `sonnet` for faster replies |
| `JARVIS_LLM_TIMEOUT_S` | 150 | after this Jarvis shows sources only |
| `JARVIS_STT_ENGINE` | `mlx` | `browser` uses Chrome/Safari's recogniser (needs internet) |
| `JARVIS_WHISPER_MODEL` | large-v3-turbo | `mlx-community/whisper-small-mlx` if the Mac feels slow |
| `JARVIS_USER_TITLE` | `sir` | how Jarvis addresses you |

## 5. Maintenance

* **Back up:** copy `data/jarvis.db`.
* **Add or refresh a law:** drop `<slug>.txt` into `data/laws/`, add its entry to `data/laws/manifest.json`, then `jarvis build` (only new text is embedded).
* **Re-run the benchmark:** `jarvis eval` writes `evaluation.csv`.
* **Re-OCR the book** (not normally needed): `brew install tesseract tesseract-lang` then `jarvis ocr --pdf "<book>.pdf"`, then `jarvis build --rebuild`.

## 6. Troubleshooting

| Symptom | Fix |
|---|---|
| Engine chip says SOURCES-ONLY | `claude` not on PATH or not logged in: run `claude` once in Terminal |
| Mic does nothing | allow microphone for the browser; `brew install ffmpeg`; or set `JARVIS_STT_ENGINE=browser` |
| Robotic voice | no internet for neural voice; the Mac system voice is used instead |
| Slow first answer | first run loads the E5 model (~470 MB) and Whisper; later answers are faster |
