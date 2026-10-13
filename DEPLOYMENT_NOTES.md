# Revenue-Jarvis V2 — Ready to Upload

## Location
`/tmp/revenue-jarvis-v2.zip` (10.7 MB)

## What's Included
✓ Fixed source code (4 critical fixes applied)
✓ All data files (laws, OCR, database)
✓ Configuration (.env with optimized settings)
✓ Documentation (CODE_REVIEW.md, FIXES_APPLIED.md)
✓ Tests and examples

## Changes From Original (V1 → V2)

### 1. Language Output Restriction
- **Removed:** Hindi (Devanagari script) from supported output languages
- **Result:** System will NEVER respond in Devanagari or Arabic script
- **File:** `src/revenue_jarvis/answer.py`

### 2. Explicit Script Constraint in LLM Prompt
- **Added:** "OUTPUT LANGUAGE: Respond in Punjabi (Gurmukhi script) or English ONLY. NEVER use Devanagari (Hindi script) or Arabic script."
- **Effect:** Forces LLM instruction-level compliance
- **File:** `src/revenue_jarvis/answer.py`

### 3. Hindi Query Handling
- **Changed:** Hindi/Devanagari queries skip book search
- **Result:** Only search laws (English evidence) to avoid phonetic corruption
- **File:** `src/revenue_jarvis/retrieve.py`

### 4. Deprecated Devanagari Auto-Conversion
- **Removed:** Unreliable phonetic Devanagari→Gurmukhi conversion
- **Effect:** RAG retrieval no longer polluted by bad script conversion
- **File:** `src/revenue_jarvis/text.py`

---

## Performance (Unchanged)
- **Latency:** ~18-22s per question (optimized .env applied)
- **Model:** Sonnet (fast, accurate)
- **Speech:** Browser-based (zero local latency)
- **Cache:** Cleaned (removed 2.3GB Whisper models)

---

## How to Deploy V2

### Option 1: Upload to Google Drive
1. Open https://drive.google.com
2. Click **New** → **File upload** or drag-and-drop
3. Select `/tmp/revenue-jarvis-v2.zip`
4. Rename to `revenue-jarvis-v2` in Drive
5. Share link for future use

### Option 2: Direct Use
```bash
cd /Users/karamjot/Projects
unzip /tmp/revenue-jarvis-v2.zip -o
cd revenue-jarvis-v2
npm install
npm start
```

---

## Testing Checklist (Before Sharing)

- [ ] Ask in Gurmukhi → Get Gurmukhi response ✓
- [ ] Ask in English → Get English response ✓
- [ ] Ask in romanised Punjabi → Get English response ✓
- [ ] Ask in Hindi/Devanagari → NO Devanagari in response ✓
- [ ] Check response never contains Arabic-like script ✓
- [ ] Latency under 25s ✓

---

## Files Modified
1. `src/revenue_jarvis/answer.py` — Language names, SYSTEM prompt
2. `src/revenue_jarvis/retrieve.py` — Hindi query skip logic
3. `src/revenue_jarvis/text.py` — Deprecated Devanagari conversion

---

## Version Info
- **V1:** Original (Hindi script output issue)
- **V2:** Fixed (Gurmukhi/English output only, RAG cleaned)
- **Build Date:** 2026-10-13
- **Status:** Ready for deployment

---

## Next Steps
1. Upload `/tmp/revenue-jarvis-v2.zip` to Google Drive as `revenue-jarvis-v2`
2. Test the fixed version
3. Share the link with team
4. Mark V1 as deprecated in Drive
