# Test report

Build date: 13 Oct 2026. Machine: Linux build box (Python 3.12, CPU only). Target machine: M1 MacBook Pro, 8 GB.

## 1. Summary

| Check | Result | Pass bar |
|---|---|---|
| Unit and failure tests (`pytest`) | **42 passed**, 0 failed | all pass |
| Lint (`ruff check`) | clean | clean |
| Book retrieval, 20-question benchmark (recall@5) | **18 / 20** | 15 / 20 |
| Book retrieval, 10 held-out questions (not used for tuning) | **10 / 10** | 8 / 10 |
| Statute retrieval, 12 benchmark questions with a known section (hit@3) | **10 / 12** | none set |
| OCR: pages with usable text | 387 / 389 | - |
| OCR: lines that failed every attempt | 1 of 12,146 | - |
| Knowledge base integrity (`PRAGMA integrity_check`, missing vectors, orphans) | ok, 0, 0 | ok, 0, 0 |
| Retrieval speed after warm-up | median 47 ms, max 15 s (first query loads the model) | - |

**Not tested here:** the live Claude Code call, Codex call, MLX Whisper and the edge-tts voice. They need your Mac, your subscription login and a microphone. The subprocess contract (flags, timeout, error text, JSON parsing, API-key stripping) is tested against stand-in `claude` and `codex` programs. Run `jarvis doctor` and ask one question on the Mac to confirm.

## 2. Benchmark design

20 questions written for a DRO's daily work: partition procedure (6), consolidation (4), village common land / shamlat (5), price fixation and acquisition compensation (3), mutation (1), abadi deh (1). Languages: English 14, Punjabi 3, Hindi 2, romanised Hindi 1. Each has gold PDF pages read from the OCR text (`tests/gold.csv`), and 12 also have gold statute sections.

A **hit** means a gold page is among the top 5 distinct book pages Jarvis hands to the model. It measures whether the right evidence reaches the answer, not whether the answer is worded correctly.

### Tuning disclosure

| Run | Book recall@5 | Change |
|---|---|---|
| 1 | 6 / 20 | plain hybrid search |
| 2 | 18 / 20 | glossary terms added to the meaning search; book keyword search uses Gurmukhi terms only; one result per page |
| 3 | 18 / 20 | statute pool follows the sections the book itself cites (law hit@3 went from 5/12 to 10/12) |

The glossary was widened while looking at the 20 benchmark questions, so 18/20 is optimistic. The 10 held-out questions (`tests/heldout.csv`: demarcation, kursinama, power-of-attorney registration, review limitation, tatima, unborn child's inheritance, nazool land, lambardar duties, clerical errors in deeds) were written afterwards and scored **10/10** without further changes.

## 3. Results by question

| Q | Topic | Lang | Gold PDF pp. | Top-5 book pages | Book hit | Statute evidence (top 3) | Law hit |
|---|---|---|---|---|---|---|---|
| Q01 | partition | en | 167 | 170, 168, 167, 183, 182 | ✓ | s.158, s.110, s.112 PLRA | ✓ |
| Q02 | partition | en | 168 | 168, 187, 170, 180, 167 | ✓ | s.117, s.118, s.111 PLRA | ✓ |
| Q03 | partition | en | 173-174 | 174, 167, 183, 168, 170 | ✓ | s.117, s.116, s.118 PLRA | ✓ |
| Q04 | partition | pa | 175-177 | 176, 29, 179, 185, 177 | ✓ | PLRM ch.18 paras | - |
| Q05 | partition | hi | 178-179 | 171, 181, 184, 167, 170 | ✗ | s.123 PLRA | - |
| Q06 | partition | en | 169-170 | 170, 183, 167, 184, 172 | ✓ | s.111 PLRA | ✓ |
| Q07 | consolidation | en | 27-29 | 27, 345, 361, 26, 349 | ✓ | s.47 Consolidation | ✗ |
| Q08 | consolidation | en | 33-51 | 225, 229, 37, 243, 242 | ✓ | - | - |
| Q09 | consolidation | pa | 52-56 | 283, 28, 52, 219, 27 | ✓ | Consolidation ss.20, 24 | - |
| Q10 | consolidation | en | 28 | 28, 65, 62, 27, 345 | ✓ | PLRM paras | - |
| Q11 | common land | en | 229-231 | 244, 236, 240, 231, 245 | ✓ | r.3, r.10, s.2 PVCL | ✓ |
| Q12 | common land | en | 228, 233-236 | 235, 232, 243, 234, 236 | ✓ | s.2 PVCL Act | ✓ |
| Q13 | common land | en | 246-247 | 247, 239, 246, 164, 194 | ✓ | s.7 PVCL Act | ✓ |
| Q14 | common land | hi | 238-239 | 239, 244, 243, 229, 66 | ✓ | r.18, r.23 PVCL Rules | ✗ |
| Q15 | common land | en | 240-243 | 240, 241, 239, 229, 242 | ✓ | r.12, r.13 PVCL Rules | ✓ |
| Q16 | price fixation | en | 278-279 | 278, 241, 94, 291, 219 | ✓ | - | - |
| Q17 | price fixation | en | 284-286 | 278, 291, 365, 94, 279 | ✗ | s.26 RFCTLARR | ✓ |
| Q18 | price fixation | pa | 287-288 | 287, 288, 284, 290, 111 | ✓ | s.73 RFCTLARR | ✓ |
| Q19 | mutation | en | 118-120 | 119, 82, 113, 124, 91 | ✓ | PLRM ch.7 | - |
| Q20 | abadi deh | hinglish | 248-249 | 248, 346, 250, 249, 324 | ✓ | - | - |

Full rows with ranks and timings: `reports/evaluation.csv` and `reports/evaluation_heldout.csv`.

### Misses and what they mean

* **Q05 (Hindi, private partition):** pages 171-184 of the partition chapter come back, but not 178-179. A Hindi question about a narrow sub-topic is the weakest case. Claude Code's keyword rewrite on the Mac should help; it isn't active in this benchmark.
* **Q17 (multiplication factor):** page 278 (price fixation) outranks 284-286. The statute evidence does include s.26 RFCTLARR, so the answer still has the right law.
* **Q07, Q14 law misses:** the consolidation text in the corpus is the Haryana version, and the PVCL Rules page mixes amendment footnotes into the rule numbers. Both are source-quality limits, flagged in `docs/SOURCES.md`.

## 4. Failure tests (all pass)

| Failure | Expected behaviour | Test |
|---|---|---|
| No `claude` or `codex` on PATH | sources-only answer with a warning | `test_missing_cli_means_sources_only` |
| CLI hangs | stopped at the timeout, sources-only | `test_claude_cli_timeout` |
| CLI not logged in / exits with error | error captured, sources-only | `test_claude_cli_error_reported`, `test_broken_engine_gives_sources_only` |
| `ANTHROPIC_API_KEY` set in the shell | removed before the CLI starts, so no API billing | `test_claude_cli_end_to_end_and_no_api_key_leak` |
| Model returns non-JSON or a bad status | sources-only | `test_broken_engine_gives_sources_only` |
| Model cites an id not in the evidence | whole answer withheld | `test_citation_outside_evidence_withholds_answer` |
| Model makes an uncited claim | claim dropped; status downgraded | `test_uncited_claims_suppressed_and_status_downgraded` |
| Prompt injection in the question | treated as data; rules restated in the system prompt | `test_prompt_injection_in_question_is_just_data` |
| Stale index (passages without vectors) | detected by `jarvis doctor`; never served | `test_stale_index_detected` |
| OCR folder missing | empty build, no crash | `test_missing_ocr_folder_gives_empty_book` |
| Unreadable page | marked `empty`, never indexed | `test_unreadable_page_is_flagged_not_indexed` |
| Incomplete or old statute text | caution shown beside the answer | `test_incomplete_law_text_is_flagged` |
| Contents pages | never used as evidence | `test_book_and_law_pools_are_separate_and_contents_excluded` |
| Table borders gluing OCR lines | rulings removed before segmentation | `test_table_rulings_removed_before_segmentation` |

## 5. Incident during the build

The first SQLite file was corrupted when a long embedding job was stopped on the build server's network file system. It was rebuilt from the OCR files; 3,391 saved vectors were checked against freshly computed ones (40 samples, minimum cosine 0.99999998) before reuse. The shipped database passes `PRAGMA integrity_check`, uses a single-file journal, and `jarvis doctor` re-checks it on your Mac.
