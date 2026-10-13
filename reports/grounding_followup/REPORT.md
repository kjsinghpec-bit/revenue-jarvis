# Answer grounding and timing follow-up

13 October 2026. Application changes are confined to `grounding.py`, `answer.py` and regression tests. Claude's OCR outputs, source PDF and staged/production database contents were not changed by this work. Measurements read the production database without writing Q&A history.

## Reproduced and repaired

- **Fee/fine amount swaps within one sentence:** the previous extractor labelled every currency amount in a sentence as both fee and fine. It now associates amounts with local labels and separates supported coordinated clauses. Regression checks cover English and Gurmukhi numerals.
- **Bare fee borrowing a citation number:** a claim such as “fee is 111” could inherit 111 from section metadata. Bare labelled amounts now require an amount-context fact from quoted text, not a locator.
- **Appeal/revision deadline swaps:** durations associated with explicit appeal/revision clauses now carry that context, rather than being interchangeable numbers of days.
- **Officer/action swaps:** having both an officer name and an action somewhere in a long quote no longer suffices for the recognized patterns. Officer/action clauses are matched together. Assistant Collector, Naib Tehsildar and Financial Commissioner are distinguished from their broader officer names.
- **Permission becoming obligation:** `shall` and `required` join `must` in the permission-to-requirement check.
- **Unrelated negation causing rejection:** recognized officer/action claims use matching source clauses for polarity/modality instead of unrelated sentences in the same quote.
- **Conflicts omitted by the model:** opposing recognized officer/action claims, or different fee/fine amounts in otherwise identical textual scopes, set status to `insufficient` and add a conflict warning. Contradictory supporting quotes cannot be pooled into a single ordinary claim. Explicit conflict notes retain their separate source requirements.

## Verification

The full suite passes **154 tests**, including 18 new follow-up cases. One upstream Starlette/httpx deprecation warning remains. The tests include true supported amounts, separate fee components, different proceedings, Gurmukhi pipeline output preserving exact English source quotes, and rejection of mixed Devanagari/Arabic generated claims. The controlled synthesis fixture tests validation and rendering; it is not a live Claude accuracy evaluation.

## Timing evidence

Detailed machine-readable measurements: `latency.json`.

| Measurement | Observed time |
| --- | --- |
| Retriever pool initialization, encoder already loaded | 249 ms |
| First local sources-only question in this run | 234 ms |
| Next two local sources-only questions | 22 ms and 17 ms |
| Historical logged partition request, retrieval | 153 ms |
| Same historical request, context assembly | 13 ms |
| Same historical request, Claude call | 28,938 ms |
| Same historical request, validation | 5 ms |

The observed long request spent approximately 99% of its recorded processing time in the Claude stage. Another historical request recorded a 5,746 ms Claude stage. These are only two historical calls; they cannot establish latency percentiles or a sub-10-second SLO.

Fresh measurements use the real cached E5 model and existing corpus. They exclude encoder loading and live LLM synthesis, run with query rewrite disabled, and must not be advertised as complete answer latency. Persisted Q&A JSON is assembled before the log commit, so its `log_commit` entry is zero; completed stage profiles in `data/timings.jsonl` are the appropriate source for that measurement.

Next performance experiment: benchmark the same questions and evidence with the configured Claude model while recording startup/synthesis time, prompt/output sizes and validation acceptance. Keep evidence and grounding checks stable during that comparison. Model/provider tuning requires live measurements; smaller embeddings are unlikely to solve the observed multi-second synthesis wait.

## Limits

These are conservative pattern checks, not semantic entailment or legal applicability verification. They do not understand every officer grade, paraphrase, condition, exception, statutory relationship or translated contradiction. Fee labels and appeal/revision context cover recognized forms only. Multi-component monetary claims and differently worded conflicts still require audit. A stored quotation can itself be wrong OCR, so Claude's transcription repair and scan review remain necessary.

Unresolved contradictions are displayed with uncertainty, not resolved by automatically assuming one source overrides another. Release gates and 95% legal-answer accuracy remain uncertified. Restart the running Jarvis application to load these changes; its live UI/Claude synthesis was not exercised during this follow-up.
