# Revenue-Jarvis Language & RAG Fixes — Applied

## Issue: System Writing in Arabic-Like Script (Devanagari)

**Root Cause:** The LLM was instructed to respond in Hindi (Devanagari script) when the user asked in Hindi. Devanagari is visually unfamiliar and was perceived as "Arabic script."

**Why This Happened:**
1. LANG_NAMES dict included Hindi as a valid output language
2. The `devanagari_to_gurmukhi()` function was auto-converting Hindi queries to Gurmukhi phonetically (unreliable)
3. RAG retrieval was treating Devanagari and Gurmukhi as interchangeable

---

## Fixes Applied

### Fix 1: Removed Hindi from Supported Output Languages
**File:** `src/revenue_jarvis/answer.py`

**Changed:**
```python
# BEFORE:
LANG_NAMES = {"pa": "Punjabi (Gurmukhi script)", "hi": "Hindi (Devanagari script)", "en": "English",
              "hinglish": "the same romanised Hindi/Punjabi mix the user wrote in"}

# AFTER:
LANG_NAMES = {"pa": "Punjabi (Gurmukhi script)", "en": "English",
              "hinglish": "Romanised Punjabi (Latin alphabet, e.g., 'takseem', 'intkal')"}
```

**Effect:** LLM will never be told to respond in Hindi/Devanagari.

---

### Fix 2: Added Explicit Script Restriction to SYSTEM Prompt
**File:** `src/revenue_jarvis/answer.py`

**Added at the top of SYSTEM prompt:**
```python
OUTPUT LANGUAGE: Respond in Punjabi (Gurmukhi script) or English ONLY. 
NEVER use Devanagari (Hindi script) or Arabic script. 
If the question is in Hindi, translate your answer to Gurmukhi or romanised Punjabi.
```

**Effect:** Forces the LLM to respect the script restriction at the instruction level.

---

### Fix 3: Hindi Queries Skip Book Search
**File:** `src/revenue_jarvis/retrieve.py`

**Changed retrieval logic:**
```python
# BEFORE:
for st, k, prefix, qtok in (("book", top_book, "B", tok_book), ("law", top_law, "L", tok_law)):

# AFTER:
lang = detect_language(q)
# Skip book search if question is in Hindi/Devanagari (unreliable script conversion)
for st, k, prefix, qtok in (
    (("book", top_book, "B", tok_book),) if lang != "hi" else ()
) + (("law", top_law, "L", tok_law),):
```

**Effect:** Hindi queries only search laws (secondary evidence in English), avoiding corrupted Devanagari→Gurmukhi conversion.

---

### Fix 4: Deprecated Devanagari Auto-Conversion
**File:** `src/revenue_jarvis/text.py`

**Removed from `alias_terms()` function:**
```python
# REMOVED:
if DEVANAGARI.search(q):
    found.append(devanagari_to_gurmukhi(q))
```

**Marked function as DEPRECATED:**
```python
def devanagari_to_gurmukhi(s: str) -> str:
    """DEPRECATED: Naive phonetic conversion is unreliable for legal terms.
    This function is kept for backward compatibility but should NOT be used for RAG retrieval.
    Use the ALIASES dict instead for accurate terminology mapping."""
```

**Effect:** Stops phonetic Devanagari→Gurmukhi corruption in RAG retrieval.

---

## Expected Behavior After Fixes

| User Input | Detection | Book Search | Law Search | Response Language |
|------------|-----------|------------|-----------|------------------|
| Gurmukhi query | `lang="pa"` | ✓ Yes | ✓ Yes | Gurmukhi or English |
| English query | `lang="en"` | ✓ Yes | ✓ Yes | English |
| Romanised (hinglish) | `lang="hinglish"` | ✓ Yes | ✓ Yes | English or Romanised |
| Hindi/Devanagari | `lang="hi"` | ✗ No (skipped) | ✓ Yes | Gurmukhi or English (NEVER Devanagari) |

---

## Testing Checklist

- [ ] Ask in Gurmukhi → Get Gurmukhi book evidence + Gurmukhi response
- [ ] Ask in English → Get Gurmukhi book evidence + English response
- [ ] Ask in romanised Punjabi → Get Gurmukhi evidence + English response
- [ ] Ask in Hindi/Devanagari → Get ONLY law evidence (no book) + Response in Gurmukhi/English (NOT Hindi)
- [ ] Check that response NEVER contains Devanagari script
- [ ] Verify latency still <25s (optimization should be working)

---

## Code Integrity

✓ All Python files compile without errors
✓ No imports broken
✓ Backward compatible (deprecated functions kept, just not called)

---

## Next Steps

1. Run the test suite: `pytest tests/`
2. Start the server: `npm install && npm start`
3. Test with various language inputs
4. Monitor evidence retrieval in the UI logs
