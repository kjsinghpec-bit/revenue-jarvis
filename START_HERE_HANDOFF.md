# Revenue Jarvis — overnight developer handoff

Snapshot: 13 October 2026, approximately 21:52 IST. This is a work-in-progress development snapshot, not a certified release. External agents may continue working after this snapshot. Work in your own extracted folder; coordinate before replacing Karamjot's running application or database.

## 1. What is included

The project archive contains the current Python source, browser UI, tests, scripts, documentation, original 389-page `Punjabi book .pdf`, official-law text files, indexed SQLite databases, OCR page JSONs, comparison images, audit reports, and `.agents/teamwork/` handoffs available at snapshot time.

Machine-specific virtual environments, Python caches, credentials, runtime logs, SQLite WAL/SHM sidecars and model caches are excluded. Each SQLite database was copied through SQLite's backup API, then personal Q&A history was removed from the copy. Source pages, chunks, dense vectors and BM25 tokens were checked unchanged by that sanitization. Production files were not changed. Full details: `PACKAGING_REPORT.json`.

The supplied `.env` is newly generated, contains no secrets, uses the local PDF, selects Claude synthesis, disables query rewrite, and uses browser speech input. Install your own dependencies and authenticate your own Claude Code session.

## 2. Verified snapshot status

The full test suite was run against this extracted snapshot, using the existing Python 3.11 environment:

**247 tests total: 242 passed, 5 failed, 0 skipped.** Exact output: `HANDOFF_TEST_OUTPUT.txt`. Machine-readable results: `HANDOFF_TEST_RESULTS.xml`.

The five failing acceptance tests are:

1. `tests/test_e2e_ocr_pipeline.py::TestTier1F2OrientationTabular::test_tier1_f2_page_382_rotated_khasra_table_structure`
2. `tests/test_e2e_ocr_pipeline.py::TestTier1F2OrientationTabular::test_tier1_f2_page_383_jamabandi_12_column_annexure_structure`
3. `tests/test_e2e_ocr_pipeline.py::TestTier1F2OrientationTabular::test_tier1_f2_page_389_khasra_girdawari_register_structure`
4. `tests/test_e2e_ocr_pipeline.py::TestTier1F2OrientationTabular::test_tier1_f2_bilingual_glossaries_no_horizontal_interleaving`
5. `tests/test_e2e_ocr_pipeline.py::TestTier1F3PrintedLabelCoverage::test_tier1_f3_staged_db_body_label_coverage_threshold`

Current active-database snapshot: 28 documents (1 book, 27 laws), 389 book pages, 3,160 chunks (947 book; 2,213 law), 3,160 embeddings, 3,160 BM25 token records, 52 body pages without printed labels. Shared copies have zero Q&A history rows.

Important synchronization gap: repaired OCR JSON text for pages 113, 167, 171, 175, 179, 183 and 261 differs from the corresponding active-database page text. Passing OCR fixture tests does not mean those repairs are searchable in the active index. Re-ingestion and fresh embedding of affected chunks remain necessary.

The current running Mac service was observed using older validator code. A restart is needed before confirming live behavior. This coding sandbox cannot manage that local service. Fresh live synthesis with the latest runtime has not been verified.

## 3. Architecture and useful files

Flow: input language detection → native-language search aliases → E5 dense retrieval + BM25 → reciprocal rank fusion → separate book and law evidence pools → Claude Code JSON synthesis → citation, quote and deterministic grounding checks → browser response and evidence links.

- `src/revenue_jarvis/retrieve.py`: hybrid search, RRF, book/law pools, evidence and timing data.
- `text.py`: Unicode normalization, language detection, tokenization and legal search aliases.
- `index.py`: dense vectors and BM25 token index.
- `ingest/book.py`, `ingest/laws.py`: page/chunk and statutory provision parsing.
- `answer.py`: prompt, JSON schema, claim validation, partial answers and deterministic spoken text.
- `grounding.py`: numeric/unit, locator, instruction, officer/action and polarity safeguards. These are limited checks, not a general entailment engine.
- `llm.py`: CLI synthesis transport and backend availability.
- `server.py`, `runtime.py`: endpoints, request timing and code/corpus revision checks.
- `page_scan.py`, `ocr_review.py`: exact original-scan mapping, OCR review provenance and import checks.
- `web/app.js` under the package: UI, source buttons, scan comparison and stale-service state.
- `scripts/run_jarvis.py`, `Start Jarvis.command`, `Restart Jarvis.command`: local launch/restart.
- `scripts/check_ocr_import.py`, `scripts/run_release_gates.py`: import and release checks.
- `scripts/repair_law_index.py`: offline cached E5 adapter and law repair reference. Do not rerun its destructive staging workflow casually.

Read `INSTRUCTIONS_FOR_CODEX.md`, `PROJECT.md`, `TEST_INFRA.md` and this handoff before coding. Historical README and reports may contain old counts, language statements or optimistic accuracy claims; the verified snapshot status above takes precedence.

## 4. Completed work worth preserving

- Grounding requires exact supporting quotes tied to their actual source IDs. Neighboring text retains its own citation; another chunk cannot silently justify a claim.
- Typed amounts, durations and locators are checked. Legal section/page numbers cannot supply unrelated fees or deadlines.
- Instruction-like output, forbidden scripts, unsupported officer powers and certain polarity/modality changes are rejected.
- English and Gurmukhi are supported output scripts. Hindi input retrieves law evidence and may synthesize English; it skips the book by the current policy.
- English book retrieval uses reviewed Gurmukhi aliases instead of being dominated by incidental English glossary tokens.
- Law provision labels were repaired; unverified legacy locators are withheld.
- Valid claims can survive rejection of other claims through the application's partial-answer mode. The response must clearly disclose that it is partial. Strict validation remains available to callers.
- Short exact quotes can expand only within the supplied cited excerpt, followed by revalidation. Fabricated quotes and unsupported numbers remain rejected.
- Speech is assembled from validated claims. Citation controls remain scoped to their own answer rather than leaking evidence across answers.
- Timings identify retrieval, synthesis and validation stages. LLM query rewrite is disabled by default.
- Source/corpus revisions flag a stale running service; changed code or indexed data requires restart before another answer.
- Original PDF identity and page matching support scan comparison. OCR review provenance is invalidated when source text/image changes; stale chunks cannot inherit verification.
- Punjabi isolated cardinal words one through ten and typed inches, centimeters, feet, meters, kanals, marlas and multipliers are now recognized. Unsupported unit substitutions and kanals/marlas swaps are rejected. Compound Punjabi number phrases and conversions are not inferred.

Earlier withheld English and Punjabi CLI outputs were replayed successfully through the repaired validator as partial answers. These are captured-output replays, not new live LLM runs. See `reports/validator_repair/REPORT.md` and its fixtures.

## 5. Book OCR: current evidence and limitations

Claude completed all 389 pages using a revised per-line segmentation threshold of 120 pixels and improved Punjabi models, with orientation probing. Four AI-transcribed partition pages previously measured approximately 12.4% to 3.4% character error reduction. That is a small, AI-referenced sample; it does not establish whole-book accuracy.

The teamwork agents subsequently repaired critical JSON passages for pages 113, 167, 171, 175, 179, 183 and 261. Tests for those target passages pass in this snapshot. Some agent handoffs claim 0% CER against their own edited reference text; do not interpret that as independent human validation.

Key critical values/clauses to compare directly with scans include the page 113 reporting period and fine multiplier; page 167 officer grade and NRI jurisdiction; page 171 sanction clause; page 175 precedent citation and 230-kanal/10-marla example; page 179 pathway width; page 183 registration-exemption and section-150 passages; page 261 standard karam and chain link counts.

Do not conflate the registration-exemption paragraph on page 183 with its separate section-150 discussion. Determine references from the actual scan and official instrument before making a legal claim.

Tables 382, 383 and 389 still need coherent row/column associations. Glossaries 346 and 368 still need layout-preserving extraction. Pages 321 and 334 contain maps; do not fabricate prose for them. Automatic orientation confidence is not proof of correct table structure.

For printed labels, `PDF page minus 15` is only a consistency check. A number may be cut off or absent; do not mark inferred labels as scan-verified to satisfy the proposed 95% coverage target.

`reports/codex_takeover/corrected_pages/` contains separate AI correction drafts for 113, 175 and 261; these were not applied to production and are not authoritative. Page 261 includes an uncertain word in the final measurement paragraph. Review against the scan; do not copy it blindly. `header_review/` contains crops for the 52 missing labels.

## 6. Setup on your own Mac

Use Python 3.11 or 3.12, preferably 3.11 to match the tested environment. The archive contains no reusable virtual environment.

From the extracted project folder:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

The provided `.env` uses browser speech recognition, avoiding a large Whisper download for initial text testing. Optional Apple Silicon voice dependencies can be installed later from `.[voice]`. The project also has `scripts/setup_mac.sh`, but it installs optional voice components and downloads the default embedding revision; use the explicit setup below to match this snapshot's known weights.

Download the known cached E5 revision once, before launching offline:

```bash
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='intfloat/multilingual-e5-small', revision='614241f622f53c4eeff9890bdc4f31cfecc418b3', allow_patterns=['*.json', '*.txt', '*.model', 'model.safetensors', '1_Pooling/*'])"
```

The active database metadata says `embed_revision=main`; the existing vectors were previously matched to the cached revision above. Avoid silently changing embeddings or downloading a different revision when comparing results. `CachedE5` expects one unambiguous local snapshot with `model.safetensors`; inspect multiple installed snapshots rather than deleting them blindly.

Install Claude Code separately if missing, then authenticate your own account from your normal Terminal. Do not copy Karamjot's authentication files. Check CLI availability with `claude --version`; use its normal interactive login flow. If synthesis is unavailable, Jarvis may show sources only.

Start:

```bash
./Start\ Jarvis.command
```

Open `http://127.0.0.1:8765/`. Keep the launcher Terminal open. If this same local Jarvis service needs replacement, use `Restart Jarvis.command`. The new launcher identifies the service before attempting to stop it; do not kill unrelated listeners. Its restart operation still needs verification in a normal Mac session.

Run tests:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_grounding.py tests/test_revenue_units.py tests/test_runtime_revision.py -q
```

Tesseract/Poppler/Punjabi language data are needed only for OCR reruns, not normal indexed text retrieval. Read `reports/ocr_repair/run_engine.py --help` and the preservation reports before starting an expensive full-book OCR run. Older build scripts may assume paths and model caches from Karamjot's Mac; adapt them on a separate staging copy.

## 7. Recommended overnight work order

1. Reproduce the five snapshot failures and inspect the actual table/glossary scans. Use targeted tests and visual comparisons. Do not weaken the assertions merely to get a green suite.
2. Preserve table cells with explicit row/column or key/value structure; mark ambiguous associations. Keep the original scan accessible beside evidence.
3. Detect printed labels from scans; retain unknown/inferred provenance where physical evidence is missing. Explain any honest shortfall in coverage.
4. Build a NEW staged database from a fresh backup of the selected baseline. Ingest the selected corrected book JSONs, regenerate affected chunks/vectors/tokens, and update review hashes. Do not reuse a stale chunk embedding after its text changes.
5. Verify all 27 law documents and 2,213 law chunks, including vectors and BM25 tokens, against baseline hashes. Preserve content; DB file bytes need not match after backup/VACUUM. Verify integrity, imports, expected page hashes and retrieval regressions.
6. Restart your own instance and run fresh English and Gurmukhi questions through actual Claude synthesis. Check supported answers, partial-answer warnings, source buttons, scan mapping and failed/uncertain cases. Record evidence, validator decisions and timings.
7. Only after correctness is demonstrated, profile warm and cold end-to-end latency. Separate model loading, query embedding, retrieval, CLI startup, synthesis and validation. Do not promise sub-10-second latency without measurement.

Useful live questions: Who decides partition cases of NRI petitioners in Punjab? Explain the page 183 section-150 passage in Gurmukhi. Ask about mutation reporting, collector fine powers and standard karam measurements. Also test deliberately wrong units, invented amounts, mismatched officer powers and prompt-injection attempts.

## 8. Acceptance and hand-back

Before proposing replacement of Karamjot's live database, provide the staged path, code diff, snapshot/baseline hashes, database import report, law-preservation report, test output, retrieval comparison, fresh live answer examples and rollback instructions. Coordinate with the other agent session so a stale snapshot cannot overwrite newer work.

Keep accuracy above speed. Never invent fees, limitation periods, officer powers, table associations or unseen page labels. Every consequential number and action must be supported by the cited source and relevant context. Passing deterministic checks is not legal advice or proof that a rule remains current.

95% citation accuracy, 90% common-question coverage, current-law applicability and whole-book OCR quality remain unmeasured. They require a defined test set and independent review. Leave the project marked development/uncertified until those gates are satisfied.

Please return a concise report of files changed, tests before/after, unresolved risks, measured latency and the exact next step. Preserve this archive as the received baseline.
