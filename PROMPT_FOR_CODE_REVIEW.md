# Prompt for GPT-6.1 Sol: Revenue-Jarvis Code Review & Optimization

---

## Context

Revenue-Jarvis is a specialized AI assistant for Punjab District Revenue Officers. It retrieves and answers questions about Punjab land law from:
- **Primary source:** Bhumbak's "Zameen Di Guide" (Gurmukhi-language book on land revenue)
- **Secondary sources:** Official acts, rules, and manuals (English)

The system uses:
- **Retrieval:** Hybrid E5 embeddings + BM25 keyword search
- **LLM Backend:** Claude Sonnet (via Claude Code CLI)
- **Output:** Grounded JSON answers with citations
- **Interface:** Web browser + voice input

---

## Current Architecture

```
User Question (Gurmukhi/English/Punjabi)
  ↓
[Language Detection] → detect_language()
  ↓
[RAG Retrieval] → search() → Book (5 results) + Laws (3 results)
  ↓
[LLM Synthesis] → Claude Sonnet → Grounded JSON answer
  ↓
[Citation Validation] → validate() → Remove uncited claims
  ↓
[Response Render] → Text/JSON with evidence links
```

---

## Files to Review

1. **src/revenue_jarvis/retrieve.py** (161 lines)
   - Hybrid retrieval with Reciprocal Rank Fusion
   - E5 dense embeddings + BM25 sparse
   - Book vs. law pool separation
   - Cross-references (xref) from citations

2. **src/revenue_jarvis/answer.py** (217 lines)
   - SYSTEM prompt design
   - JSON schema validation
   - Citation validation
   - Grounded answer synthesis

3. **src/revenue_jarvis/text.py** (141 lines)
   - Language detection (Gurmukhi/Hindi/English/hinglish)
   - Tokenization
   - Search aliases (English ↔ Gurmukhi glossary)
   - OCR cleanup

4. **src/revenue_jarvis/index.py**
   - Embedding indexing
   - BM25 tokenization

5. **src/revenue_jarvis/db.py**
   - SQLite schema
   - Chunk storage & metadata

6. **src/revenue_jarvis/server.py**
   - Web API endpoints
   - Request/response handling

7. **src/revenue_jarvis/llm.py** (90 lines)
   - Claude Code CLI wrapper
   - Codex CLI fallback
   - Timeout handling

---

## Known Issues to Address

### Language & RAG (Recently Fixed)
- ✓ Removed Hindi output (no Devanagari responses)
- ✓ Skip book search for Hindi queries
- ✓ Removed phonetic Devanagari→Gurmukhi conversion

### Performance
- Current latency: 18–22 seconds per question
- Bottleneck: Two LLM calls (if query rewrite enabled)
- Goal: < 10 seconds without accuracy loss

### Retrieval Quality
- Book-heavy bias (5 results vs 3 law results)
- Cross-references (xref) weighted 3× (may over-index cited acts)
- BM25 tokenization may miss legal compounds

### RAG Grounding
- OCR errors in book may cause false citations
- Evidence window (450 chars) may cut off important context
- No semantic chunking (fixed-page chunks)

### LLM Integration
- Single LLM model (Sonnet) — no fallback for complex cases
- Timeout 150s — may kill long syntheses
- JSON validation too strict (some valid answers rejected)

---

## Questions for GPT-6.1 Sol

### A. Code Quality & Architecture

1. **Retrieval Design**
   - Is Reciprocal Rank Fusion the right fusion method for legal docs?
   - Should book and law pools be weighted differently (currently 5:3)?
   - Are cross-reference weights (3×) too aggressive?
   - Is E5 embeddings optimal for Punjab legal Hindi/Punjabi/English mix?

2. **LLM Prompt**
   - Is the SYSTEM prompt clear enough for Sonnet?
   - Are the JSON schema constraints too tight (suppressing valid answers)?
   - Should we add in-context examples (few-shot)?
   - How can we reduce the "sources_only" fallback rate?

3. **Citation Validation**
   - The `validate()` function rejects uncited claims — is this too strict?
   - Should we allow "soft citations" (claims with weak evidence)?
   - How do we handle OCR errors in evidence text?

### B. Performance & Latency

1. **Reduce 18–22s → < 10s without accuracy loss**
   - Skip LLM query rewrite entirely? (Already in .env)
   - Use smaller embeddings (E5-small vs E5-large)?
   - Implement caching for repeated questions?
   - Pre-compute dense + sparse retrieval rankings?
   - Use distilled/quantized Claude model?

2. **Optimize Retrieval**
   - Current depth=30 candidates before RRF — too high?
   - BM25 score threshold — should we drop low-scoring matches?
   - Can we batch retrieve book + law in parallel?

3. **LLM Optimization**
   - Multi-turn synthesis (break complex Q into sub-questions)?
   - Streaming response (return first claim while fetching next)?
   - Shorter SYSTEM prompt (reduce token overhead)?

### C. Reliability & Hallucination Prevention

1. **Evidence Quality**
   - How do we detect & flag OCR errors before citation?
   - Should we re-rank evidence by "citation confidence"?
   - Can we add temporal disclaimers ("this ruling is from 1950")?

2. **Fallback Strategy**
   - Current: If LLM fails → show sources only
   - Better: Detect partial answers vs. failed ones?
   - Should we have a secondary answer engine (rules-based)?

3. **Validation Beyond Citations**
   - Should we check if cited text actually supports the claim?
   - Detect self-contradictions across book vs. law evidence?
   - Validate dates/numbers extracted from evidence?

### D. Feature Completeness for Real Revenue Officer Use

1. **Missing Capabilities**
   - Should we support form generation (e.g., mutate application form templates)?
   - Can we track case history (prior Q+A for same case)?
   - Should we flag precedent conflicts (this act supersedes that ruling)?
   - Can we compute deadlines (statute of limitations)?

2. **User Experience**
   - Should we auto-suggest related questions (NyaYa-style)?
   - Can we explain why we're uncertain ("missing context" vs "conflicting sources")?
   - Should we support footnote-style explanations?
   - Can we generate a PDF brief from an answer?

3. **Officer Workflow**
   - Should answers include officer actions (e.g., "Tehsildar must...Patwari must...")?
   - Can we extract authority hierarchy (who decides, who appeals)?
   - Should we flag which officers CAN and CANNOT do something?

### E. Data & Training

1. **Book Coverage**
   - What % of Punjab revenue law is in Bhumbak's book vs. acts/rules?
   - Are there gaps (e.g., recent amendments, local orders)?
   - Should we add case law / court judgments?

2. **Embedding Quality**
   - Is E5 trained on legal text? (May have domain gap)
   - Should we fine-tune embeddings on Punjab revenue corpus?
   - Can we use legal-specific embeddings (LegalBERT)?

---

## Success Criteria

For Jarvis to be a **real revenue assistant**, it should:

1. **Speed:** Answer in < 10 seconds (network + LLM)
2. **Accuracy:** Cite correct evidence 95%+ (audit on test set)
3. **Coverage:** Handle 90%+ of common revenue officer Q's
4. **Confidence:** Clearly flag uncertain/conflicting answers
5. **Action:** Tell officer WHAT TO DO (not just recite law)
6. **Compliance:** Never hallucinate fee amounts, deadlines, or powers
7. **Scalability:** Handle 100+ Q's/day without slowdown
8. **Language:** Fluent Gurmukhi + English (no Devanagari)

---

## Code Artifacts Provided

- **Full source code:** `/Users/karamjot/Projects/revenue-jarvis/src/`
- **Data files:** `/Users/karamjot/Projects/revenue-jarvis/data/` (laws, OCR, embeddings)
- **Tests:** `/Users/karamjot/Projects/revenue-jarvis/tests/`
- **Docs:** CODE_REVIEW.md, FIXES_APPLIED.md, DEPLOYMENT_NOTES.md
- **Packaged:** `/tmp/revenue-jarvis-v2.zip` (ready to analyze)

---

## Ask for GPT-6.1 Sol

**Please perform a comprehensive code review and optimization analysis covering:**

1. **Bug Detection:** Identify all bugs, edge cases, and potential crashes
2. **Performance Bottlenecks:** Find where latency is hidden (profiling)
3. **Architectural Issues:** Is the retrieval + LLM pipeline sound for legal QA?
4. **Data Quality:** Are embeddings, tokenization, and chunking optimal?
5. **Prompt Engineering:** Can the SYSTEM prompt be improved for better grounding?
6. **Reliability:** How do we prevent hallucination and false citations?
7. **Feature Gaps:** What's missing to make this a real officer tool?
8. **Implementation Roadmap:** Prioritized steps to 10s latency + 95% accuracy

---

## Tone & Constraints

- **Assume:** This is a production system for a busy revenue officer
- **Prioritize:** Accuracy > speed (wrong answer is worse than slow answer)
- **Constraints:** Running on Mac with 8GB RAM, Claude Sonnet API via CLI
- **Scope:** Focus on code, algorithms, prompts (not new data collection)
- **Deliverable:** Actionable recommendations with code sketches where relevant

---

## Questions to Ask Yourself (as GPT-6.1)

- If I were a Punjab revenue officer, would I trust this answer?
- What's the worst thing this system could do (wrong deadline, unauthorized action)?
- How would I debug a wrong answer (tracing evidence back to source)?
- Can I explain my reasoning to the officer (transparent citations)?
- What would make me 10x more useful to the officer?

---

End Prompt.
