# Grounding repairs and release verification — 13 October 2026

Implemented the scope in `INSTRUCTIONS_FOR_CODEX.md`. E5 + BM25 + RRF, book/law pools, and the numbered SYSTEM-prompt structure remain in place. The sketches were corrected where they contradicted their intended behavior.

## Implemented changes

1. **Instruction checks:** generated claims are screened for meta-instructions, file/command requests, and the urgent approval patterns in the instructions. Genuine supported statutory permissions are not rejected merely for containing “may” or “must.” Claude runs with a replacement grounding prompt, safe mode, no built-in tools, no MCP configuration, and skills disabled. The Codex adapter withholds synthesis because its read-only sandbox cannot establish tool-free execution; it returns a handled error and sources remain available.
2. **Numeric checks:** amounts, dates, percentages, and time periods are checked against the claim's own supporting quotes. English number words and Gurmukhi digits are normalized. A fee cannot borrow a fine from a separate sentence, or an amount from another cited/unrelated source. A year cannot borrow a days value. A numerical match alone is not proof of legal applicability.
3. **Citation grounding:** each cited source needs an exact supporting quote. Legacy extractive responses are accepted only if their claim text occurs in the cited source. Same-script overlap, role, polarity and permission checks reject obvious unrelated claims and changes of meaning. Translations require source quotes; word overlap is not used across scripts. Explicit page/provision numbers and provision kinds are checked against stored metadata.
4. **Spoken output:** the model's independent spoken legal conclusion is discarded. Speech is assembled from surviving validated claims; withheld answers receive a fixed explanation. Auxiliary fields are screened and numerical/operational auxiliary assertions are suppressed.
5. **Adjacent context:** neighboring chunks have independent SIDs, text, pages, section numbers and provision kinds. Neighbor text is no longer attributed to the original chunk's locator.
6. **Law structure:** lowercase paragraph headings are recognized; preambles are preserved. Contents, schedules, annexures and appended separate instruments are retained as excluded reference chunks rather than mislabeled sections. Combined Act/Rules material has explicit section/rule kinds. Legacy law locators without `structure_v2` are not presented as verified and cannot support synthesized claims.
7. **Hindi synthesis:** law-only evidence reaches the synthesis path and can produce an answered result via `law_support`. Hindi input receives English output. Input and reply language are separate; TTS uses reply language. Deprecated phonetic script conversion is removed from the active reverse-glossary path; explicit Hindi aliases are used. Shared Punjabi danda punctuation is allowed, while generated Devanagari/Arabic text is rejected.
8. **Rewrite:** disabled by default and skipped at the call site when off. Opt-in rewrite terms now reach retrieval; they no longer incur a call without affecting search.
9. **UI:** full UUID answer IDs are attached to evidence. Each message's citation handlers close over that message's evidence. Earlier B1 buttons continue to open earlier B1 pages after later answers arrive.
10. **Profiling and gates:** timings cover detection, encoding, pool ranking, context, synthesis, validation, database commit, server queue wait and initialization. `data/timings.jsonl` persists measurements without copying questions/prompts. Browser console timing records request-to-render; transcription is measured separately. The release runner checks grounding, citations, output language, live HTTP latency and usable coverage. Missing live results or missing human audits block certification.

## Schema change

Every paraphrased/translated claim, law point and conflict needs supporting quotations:

```json
{
  "text": "A source-supported explanation in the reply language",
  "source_ids": ["L1"],
  "support": [{"source_id": "L1", "quote": "Exact text from L1"}]
}
```

Quotes must preserve decisive conditions and exceptions. Claims in `claims` need book support; `law_support` needs law support; a book/law conflict needs both sides. Unknown IDs, false quotes and unsafe numeric/locator changes withhold synthesis. Strict checks can increase sources-only results; the live audit must measure this tradeoff.

## Database repair

The active `data/jarvis.db` has been rebuilt for law structure. The original is preserved at `data/jarvis.before-grounding-20261013.db`; activation hashes are in `reports/grounding_fixes/activation.json`.

No model or legal source was downloaded. The existing cached E5 snapshot is `614241f622f53c4eeff9890bdc4f31cfecc418b3`. Because sentence-transformers was unavailable in this shell, the repair used Hugging Face's direct E5 mean-pooling/normalization path. Twenty stored vectors matched fresh vectors with minimum cosine **0.99999988** before reuse. The repair reused 1,827 law vectors and re-embedded 386 changed chunks. The database now contains 3,157 chunks/vectors, no missing vectors or orphans, and an `ok` integrity check. All 27 law documents remain represented; reference chunks are preserved but excluded from operational retrieval.

The repair script stages a database and verifies it before activation. See `scripts/repair_law_index.py` and `reports/grounding_fixes/index_repair.json`. The checked staged copy remains at `reports/grounding_fixes/jarvis.staged.db`. Running servers must restart to load the changed code and database into their cached retrievers. Restore the backup only with the server stopped and preserve newer Q&A history before a rollback.

## Verification and measurements

The final full test run passed **118 tests**, with one upstream deprecation warning. Tests include instruction patterns, invented fees in several formats, wrong-source amounts, wrong units, wrong roles, changed permission, false quotes, wrong page/provision kinds, spoken suppression, Hindi synthesis, answer/evidence UUID binding, legacy locator safety, per-answer citation clicks, disk profiles and release-gate behavior. Structural tests cover all 27 local law files. They establish parser regressions, not independent legal certification of those sources.

`pytest` runs use real BM25/Pydantic/FastAPI/SQLite. Encoding and LLM responses are controlled in unit tests; the UI test executes production rendering and click functions with DOM adapters. A full browser citation audit is still required. The local test environment was recovered from cached packages plus the upstream BM25 source (`d20a28e82d82520ff23a9f4684a26b01f5e8d7d7`). PyPI DNS was unavailable; no production dependency installation was performed. One upstream Starlette/httpx deprecation warning remains.

The actual cached E5 model was exercised separately. Ten retrieval samples measured **19.5 ms median**, **246.2 ms maximum** including the first-query warm-up. These exclude LLM, HTTP transit and voice. See `reports/grounding_fixes/retrieval_profile.json`. They do not establish a production answer-latency SLO.

The live Claude probe reached the CLI but returned **“Not logged in · Please run /login”**, with zero API processing time. Thus the reported historical 18–22 seconds cannot be attributed to stages yet. The failed pipeline probe recorded about 223 ms retrieval and 3.3 s CLI failure handling. No valid live synthesis timing, 95% support audit or 90% usable-coverage claim has been established.

## Running production gates

In the normal application environment:

```sh
claude auth login
python -m pytest -q
jarvis serve
```

With the server running, in another terminal:

```sh
python scripts/run_release_gates.py --collect --url http://127.0.0.1:8765
```

The runner collects 50 actual HTTP round trips over `tests/release_questions.json` (existing benchmark questions plus ten authored Hindi inputs). It records results in `reports/live_release.jsonl`; it does not manufacture audits. Running it again replaces the measurement file, so archive reviewed results first. These prompts are a reproducible starting set, not proof of representative officer-task coverage.

For each distinct answer reviewed against its source, add an audit bound to that exact answer:

```json
{
  "reviewer": "Reviewer name",
  "answer_id": "The actual answer UUID",
  "answer_sha256": "The collected answer_sha256 value",
  "numeric_correct": true,
  "supports_claims": true,
  "citation_correct": true,
  "clicked_citations": true
}
```

Set these flags only after checking every material claim, its conditions/actor, original OCR where decisive, and every citation click. Add this object as `audit` in its measurement record. Changing an answer invalidates its audit hash. Then run:

```sh
python scripts/run_release_gates.py --results reports/live_release.jsonl
```

Exit 0 requires all five gates to pass. Grounding/citation need 20+ distinct audited questions; coverage needs 30+ distinct audited questions and at least 90% supported substantive answers. Language needs 10+ distinct Hindi synthesis results without prohibited script. Latency needs 50 validated live responses at median ≤15 s and p95 ≤25 s, measured at the HTTP client. `reports/release_gates.json` currently records all five gates as **blocked**, not passed.

## Remaining limits

Deterministic checks and exact quotes do not establish full semantic entailment, correct translation, complete conditions, current amendments, or applicability. A sophisticated unsupported paraphrase can still evade word/pattern checks. No finite regex or test set proves “never hallucinate.” Source scans, bilingual review and the bound audit remain required; the software must not be declared production-ready from unit results alone.

The existing Haryana/version-limited texts remain version-limited; their warnings are now visible to synthesis. Source parsing fixes cannot supply missing Punjab amendments. This work changes no statutory data, introduces no automatic officer decisions or deadline calculators, and makes no coverage-percentage claim.

Current blockers for production certification are Claude authentication, live validated measurements and the source/translation/citation audit. No merge or deployment was performed; this folder is not a Git repository.
