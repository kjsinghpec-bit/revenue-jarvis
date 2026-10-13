# Revenue-Jarvis Code Review: Language & RAG Issues

## Issues Found

### 1. **CRITICAL: Arabic Script in LLM Output (Language Constraint Missing)**

**Location:** `src/revenue_jarvis/answer.py`, line 26-27

**Problem:**
The `LANG_NAMES` dict includes Hindi (Devanagari), but the SYSTEM prompt instructs the LLM to respond in `LANG_NAMES.get(lang, "English")`. However:
- Hindi (Devanagari script) is **NOT** explicitly restricted in the prompt instructions
- If a user asks in Hindi or the system detects Devanagari, the LLM may respond in Devanagari (Hindi), and Devanagari ≠ Gurmukhi
- The prompt says "Reply language: {lang_name}" but doesn't restrict output — LLM may ignore this

**Current Code:**
```python
LANG_NAMES = {
    "pa": "Punjabi (Gurmukhi script)",
    "hi": "Hindi (Devanagari script)",
    "en": "English",
    "hinglish": "the same romanised Hindi/Punjabi mix the user wrote in"
}
```

**Fix Required:**
Remove Hindi from the supported output languages. Only allow:
- Punjabi (Gurmukhi script)
- English
- Romanised Punjabi/Hindi (hinglish)

---

### 2. **RAG Language Pool Mixing**

**Location:** `src/revenue_jarvis/retrieve.py`, lines 113-118

**Problem:**
The retrieval system mixes languages aggressively:
- `bridge = alias_terms(q)` → converts English/Hindi queries to Gurmukhi
- `english = english_terms(q)` → adds English statute words
- `tokenize()` treats Devanagari and Gurmukhi equally in BM25 scoring

When a Hindi (Devanagari) question is asked:
1. Line 128-129 in `text.py` auto-converts Devanagari to Gurmukhi **phonetically** (not semantically correct)
2. This pollutes the RAG embedding vector with noise from bad transliteration

**Current Code (text.py, line 44-54):**
```python
def devanagari_to_gurmukhi(s: str) -> str:
    """Approximate script transliteration (the two Unicode blocks are aligned by design)."""
    out = []
    for ch in s:
        cp = ord(ch)
        if 0x0905 <= cp <= 0x0963:
            g = chr(cp + 0x100)  # <-- NAIVE: assumes direct Unicode offset mapping
            out.append(g if unicodedata.name(g, \"\") else ch)
        else:
            out.append(ch)
    return \"\".join(out)
```

This is **phonetically plausible** but semantically wrong. It assumes Devanagari→Gurmukhi offset is always +0x100, which works for vowels but fails for ligatures.

**Fix Required:**
1. Only accept **Gurmukhi queries** for the book (primary evidence)
2. For Hindi/English queries → only search the laws (secondary evidence)
3. Remove the `devanagari_to_gurmukhi()` conversion from the retrieval flow

---

### 3. **Language Detection Includes Hindi, LLM Output Not Validated**

**Location:** `src/revenue_jarvis/text.py`, lines 62-74 & `answer.py`, line 179

**Problem:**
`detect_language()` returns `"hi"` (Hindi) as a valid output language, but the book is **Gurmukhi only**. The LLM is told to respond in Hindi if the user asked in Hindi, but:
- The evidence is Gurmukhi (book) + English (laws)
- LLM generating Hindi response creates a mismatch

**Current Behavior:**
```
User asks in Hindi (Devanagari) 
  ↓
detect_language(q) → "hi"
  ↓
SYSTEM prompt says: "Reply language: Hindi (Devanagari script)"
  ↓
LLM responds in Devanagari 
  ↓
User sees Arabic-script text (they saw it as "wrong script")
```

---

## Recommended Fixes

### Fix 1: Restrict Output Languages in SYSTEM Prompt

**File:** `src/revenue_jarvis/answer.py`

Replace lines 26-27 and lines 41-42:

```python
# BEFORE:
LANG_NAMES = {
    "pa": "Punjabi (Gurmukhi script)",
    "hi": "Hindi (Devanagari script)",
    "en": "English",
    "hinglish": "the same romanised Hindi/Punjabi mix the user wrote in"
}

# AFTER:
LANG_NAMES = {
    "pa": "Punjabi (Gurmukhi script)",
    "en": "English",
    "hinglish": "Romanised Punjabi (Latin alphabet, e.g., 'takseem', 'intkal')"
}
```

And update the SYSTEM prompt (line 41) to:

```python
# BEFORE:
9. Reply language: {lang_name}. Keep legal terms in their usual form (e.g. intkal, tatima, shamlat) where natural.

# AFTER:
9. Reply language: {lang_name}. NEVER respond in Devanagari or Arabic script. Keep legal terms in their usual form (e.g. intkal, tatima, shamlat) where natural. If the user asked in Hindi (Devanagari), translate your answer to Punjabi Gurmukhi script or romanised Punjabi.
```

---

### Fix 2: Remove Devanagari-to-Gurmukhi Conversion from RAG

**File:** `src/revenue_jarvis/retrieve.py`, lines 113-118

Replace with:

```python
def search(self, question: str, extra_terms: list[str] | None = None, top_book: int = 5, top_law: int = 3) -> list[Evidence]:
    q = question.strip()
    lang = detect_language(q)
    
    # Only search the book if question is in Gurmukhi or English
    # If Hindi/Devanagari, search only laws (secondary evidence)
    bridge = alias_terms(q) if lang != "hi" else []
    english = english_terms(q)
    
    qv = encode_query(self.model, (q + " " + " ".join(bridge + english)).strip())
    tok_book = tokenize(" ".join(bridge)) if bridge and lang == "pa" else tokenize(q)
    tok_law = tokenize(q + " " + " ".join(bridge + english))
    
    out: list[Evidence] = []
    cites = extract_citations(q)
    
    # Book search only for Gurmukhi/English; skip for Hindi
    if lang != "hi":
        for st, k, prefix, qtok in [("book", top_book, "B", tok_book)]:
            pool = self.pools[st]
            seen: set = set()
            n = 0
            for cid, score, rk in self._rank(pool, qv, qtok, None):
                m = pool.meta[pool.index[cid]]
                key = m["pdf_page_start"]
                if key in seen:
                    continue
                seen.add(key)
                n += 1
                out.append(Evidence(...))
                if n >= k:
                    break
    
    # Laws search always available
    pool = self.pools["law"]
    xref = self._xref_indices(pool, cites)
    seen: set = set()
    n = 0
    for cid, score, rk in self._rank(pool, qv, tok_law, xref):
        m = pool.meta[pool.index[cid]]
        key = (m["short_name"], m["section"] or m["text"][:80])
        if key in seen:
            continue
        seen.add(key)
        n += 1
        out.append(Evidence(...))
        if n >= top_law:
            break
    
    return out
```

---

### Fix 3: Remove Devanagari Function from text.py

**File:** `src/revenue_jarvis/text.py`, lines 44-54

This function is no longer needed. Mark it as deprecated:

```python
def devanagari_to_gurmukhi(s: str) -> str:
    """DEPRECATED: Naive phonetic conversion is unreliable. Use only for glossary lookups, never for RAG retrieval."""
    # ... keep the function for backward compatibility, but don't use it in retrieve.py
```

Remove the call in `text.py` line 129:
```python
# BEFORE:
if DEVANAGARI.search(q):
    found.append(devanagari_to_gurmukhi(q))

# AFTER:
# Devanagari auto-conversion removed — use explicit ALIASES dict instead
```

---

### Fix 4: Add Language Constraint to Prompt

**File:** `src/revenue_jarvis/answer.py`, line 29-50

Add explicit constraint early in SYSTEM:

```python
SYSTEM = """You are JARVIS, the personal revenue-law aide of a Punjab District Revenue Officer. Address him as "{title}".
Tone: calm, precise, courteous, brief - like a trusted senior aide.

OUTPUT LANGUAGE: You must respond in Punjabi (Gurmukhi script) or English ONLY. Never respond in Devanagari (Hindi script) or Arabic script. If the question is in Hindi, translate your answer to Gurmukhi or romanised Punjabi.

ABSOLUTE RULES
...
"""
```

---

## Summary of Changes

| File | Lines | Change | Impact |
|------|-------|--------|--------|
| `answer.py` | 26-27 | Remove Hindi from `LANG_NAMES` | Prevents LLM from being told to respond in Hindi |
| `answer.py` | 41-42 | Add "Never respond in Devanagari" to prompt | Forces LLM to respect script restriction |
| `answer.py` | 29-50 | Add explicit OUTPUT LANGUAGE section | Clear instruction before rules start |
| `retrieve.py` | 113-118 | Skip book search for Hindi queries | Stops polluted Devanagari→Gurmukhi conversion |
| `text.py` | 129 | Remove Devanagari auto-conversion from aliases | Prevents phonetic corruption of RAG |

---

## Testing After Fixes

Test these scenarios:

1. **Gurmukhi query** → Gurmukhi book + English laws + Gurmukhi response ✓
2. **English query** → Gurmukhi book + English laws + English response ✓
3. **Hindi query** → English laws only + Gurmukhi/English response (NOT Hindi) ✓
4. **Romanised (hinglish) query** → Gurmukhi book + English laws + English/Gurmukhi response ✓

---

## Root Cause Analysis

The system was designed to be **language-agnostic**, treating Devanagari and Gurmukhi as interchangeable via Unicode offset math. This is **wrong for legal documents**:
- Gurmukhi is the **official script for Punjab land law**
- Hindi (Devanagari) is a different language with different legal terminology
- Users seeing "Arabic-like script" = LLM responding in Devanagari, which you never wanted

**The fix:** Explicitly restrict the system to Gurmukhi + English + romanised Punjabi only. Reject Hindi/Devanagari as an input language for the book search.
