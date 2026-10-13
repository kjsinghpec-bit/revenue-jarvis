# Retrieval failure follow-up

13 October 2026. Reproduced the question in Q&A log entry 3: “what is the prcedure of partition of land”.

## Confirmed causes

1. The answer was withheld by `grounding.check_support()` for unsupported numeric value `1887`. The response had retrieved sources and completed its Claude call. The earlier validator treated a source-established year in an Act's name as an independently asserted numeric fact. This was a false rejection introduced by the grounding repair.
2. Book BM25 searched the entire English question even when Gurmukhi bridge terms existed. English glossary/table pages gained lexical ranks and crowded out procedural material. Conversely, mixed Punjabi/English queries could discard specific native words whenever a bridge term existed.

The database is not corrupt: its integrity check passes, 914 book chunks on 372 body pages and 1,919 law chunks are searchable, and 27 law/rule/manual documents are stored. That proves indexing presence, not complete legal coverage or OCR fidelity. Rules available online are not automatically available to this local search; their text must be ingested.

## Changes

- Book sparse queries preserve native Gurmukhi terms and numbers, add the legal glossary terms, and omit incidental English words when bridge terms exist. Dense encoding, RRF weights, pool quotas and embeddings are unchanged.
- Only the occurrence of a verified instrument year within its name is exempted from amount/date checks. A second occurrence asserted as a fee/deadline remains checked. The instrument must be established in the cited source or its stored title; another unrelated source cannot supply it.
- Regression tests cover the observed English/native query-token failures, acceptance of the named Act/year and rejection of reuse of that year as a fee.

## Verification

The real cached E5 model reproduced the old query behavior and the changed behavior on the same database. For the exact logged question, the top book pages changed from **187, 346, 368, 170, 169** to **170, 167, 183, 184, 231**. The noisy glossary pages 346 and 368 no longer occupy the evidence set. With corrected spelling, “What is the procedure for partition of land?” returns **170, 167, 184, 183, 182**, plus PLRA sections **112, 111, 116**.

Existing benchmark and held-out CSVs contain 27 non-Hindi queries under the current skip-book-for-Hindi policy. Correct-book-page hit@5 improved from **23/27 to 27/27**, using an ablation of the old sparse preprocessing versus the new preprocessing. This is an existing development benchmark, not a new independent answer-accuracy audit. Full results: `retrieval_followup.json`.

The full test suite passes **122 tests**, with one upstream deprecation warning. Fee, deadline, false-quote, locator and instruction checks still pass. No database re-ingestion was performed for this follow-up.

## Observed latency and remaining verification

The actual failed request's persisted profile records about **153 ms retrieval**, **13 ms context assembly**, **28,938 ms Claude synthesis** and **5 ms validation**. Its long wait was spent in synthesis; the complete answer was then withheld. These are one request's measurements, not a latency SLO.

The browser connection to port 8765 was refused during verification, so the changed pipeline has not been retested with a live synthesized answer through that server. Restart `Start Jarvis.command` to load the updated modules and repeat the partition question. The normal Terminal's Claude call was working in the observed Q&A log; the agent's authentication environment is different.

OCR fidelity, support completeness, translated claims and applicability still require audit. A matching page or valid quotation does not prove a legally correct answer. Production release gates remain uncertified.
