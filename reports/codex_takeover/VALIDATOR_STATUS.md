# Validator work — 13 October 2026

Implemented in `src/revenue_jarvis/grounding.py`:

- Recognise isolated Punjabi cardinal words from one through ten, including written deadlines and multipliers.
- Bind supported numbers to inches, centimeters, feet, meters, kanals, marlas and multipliers. A matching number alone cannot justify changing its unit.
- Preserve whole-token boundaries for Gurmukhi. `ਪੰਜਾਹ` cannot supply `5` from the prefix `ਪੰਜ`.
- Do not infer unit conversions or compound Punjabi number phrases.

Verification:

- Initial revenue-unit tests: 3 failed, 2 passed before the fix.
- After the fix: all initial 5 tests passed.
- Extended grounding, revenue-unit and runtime revision checks: 43 passed.
- Full suite before the last two boundary tests were added: 222 passed, 11 failed. All failures were in existing OCR repair, table structure, glossary layout or printed-label acceptance checks.

Limits:

- These deterministic checks do not prove semantic entailment or current legal applicability.
- The production database and Claude team's OCR artifacts were not modified by this validator change.
- The previously observed live service used older code. A restart in the user's normal Mac session is needed before live answer verification; this sandbox cannot manage that service.
