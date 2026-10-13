# Withheld-answer repair

13 October 2026. No OCR extraction, database replacement or source PDF modification was performed in this follow-up.

## What actually failed

Recovered the original assistant JSON from the local Claude CLI session records matching the two logged Jarvis questions. This makes diagnosis possible without guessing at the withheld model text.

- English NRI partition answer: three claims pass the corrected checks. A fourth extra claim cites section 126 and Assistant Collector 1st Grade, but its narrow quote does not support the officer/rank. Previously one rejected point withheld the entire answer.
- Punjabi shared-land answer: the first supporting quote ends immediately before the printed section number. Other quotes omit the instrument year/authority context that occurs elsewhere in the same cited excerpt. They are exact but too short to support the proposed whole claims.
- The `1.5E+2` message is the old Decimal representation of 150. Exponent notation itself was not evidence of OCR corruption or a sufficient diagnosis of the failure. The missing quote/locator support was the material issue.

## Changes

1. Explicit section/rule/paragraph references can be established by typed references in the quoted source; book references can also be established in the same cited book excerpt, which has page metadata rather than a structured law-section field. Wrong references still fail.
2. Locator numbers are masked only at validated locator occurrences. Metadata cannot provide an arbitrary count, fee or duration.
3. Known numeric values use plain decimal formatting (`150`, not `1.5E+2`).
4. The app validates claims independently. Supported claims survive an unsupported addition. The response sets `partial_answer=true`, warns that points were omitted, and announces that it is partial in spoken text. If no supported legal claim survives, fallback remains.
5. A short, exact quote can be expanded to its own already-retrieved cited excerpt and rechecked. This never uses another source ID, missing neighbor text, a fabricated quote or another LLM call. Unsupported amounts and officer/action changes still fail. Explicit conflicts are not silently resolved.

Strict `validate()` mode remains the default for direct callers; the answering pipeline explicitly enables partial validation. Broader semantic entailment, translated conditions and applicability still require audit. A preserved claim is not a certification of current law or perfect OCR.

## Verification

The original two Claude responses were replayed through the real retrieval/answer pipeline using the active repaired database and cached E5 encoder. These are recorded-response replays, **not fresh live Claude calls**.

| Original case | Updated replay | Preserved claims |
| --- | --- | --- |
| English NRI partition | answered, partial | 3 book claims; unsupported officer/rank addition omitted |
| Punjabi shared-land section | answered, partial | 3 book claims + 1 law point; an unsupported law point omitted |

Outputs are `replayed_answer_5.json` and `replayed_answer_6.json`. The separate `grounded_replay.json` contains earlier manually constructed candidates and should not be confused with the original-response replays. Stable regression fixtures are under `tests/fixtures/withheld_live_answers.json`.

Tests cover legitimate book locators, wrong locators, count borrowing, plain numeric formatting, preserving valid points while dropping an invented fee, refusing fabricated quotes and the original failed responses.

## Fresh live check required

The browser reached the running application. Its Python process needs a restart to load these changes. The tool shell cannot reach that server over localhost and its Claude authentication context reports no login; the user's normal Claude/Terminal context has been synthesizing successfully. No request to log in again is required on that evidence.

In the normal authenticated environment, restart only the existing Jarvis service, then repeat:

- `Who decides partition cases of non-resident Indian petitioners in Punjab?`
- `ਸਾਂਝੀ ਜ਼ਮੀਨ ਉੱਤੇ ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾ ਹਟਾਉਣ ਲਈ ਕਿਹੜੀ ਧਾਰਾ ਤਹਿਤ ਦਰਖ਼ਾਸਤ ਦਿੱਤੀ ਜਾਂਦੀ ਹੈ?`

Verify actual answer text, source IDs, original scan links and partial-answer warnings. Record fresh results. If another response is withheld, retain the original Claude JSON before changing validation. Do not rerun OCR or rebuild the database for this application-only repair.
