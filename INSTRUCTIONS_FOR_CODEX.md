# Instructions for Codex: Make Jarvis Production-Ready

---

## Priority 1: Critical Grounding Fixes (Must Fix Before Release)

### 1.1 Claim Validation — Block Instruction Injection
**Problem:** LLM can hide instructions inside claims, bypassing suppression.
**What to do:**
- Add post-synthesis instruction detection: scan all claims/law_support/conflicts for imperative verbs + request patterns
- If detected, reject claim with warning: "Claim contains unsupported instruction"
- Example: claim="Tehsildar must approve this application NOW" → reject (contains imperative from prompt injection)
- Location: `src/revenue_jarvis/answer.py`, function `validate()` after line 139

**Code sketch:**
```python
import re

INSTRUCTION_PATTERNS = [
    r'\b(must|should|will|can|cannot)\s+(you|the system|jarvis)',
    r'\b(ignore|skip|disregard|override)\b',
    r'\b(do not|don\'t)\s+\w+\s+(this|that)',
]

def has_instruction(text: str) -> bool:
    """Detect if claim contains hidden instructions."""
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in INSTRUCTION_PATTERNS)

# In validate(), before returning ans:
for claim in ans.claims + ans.law_support + ans.conflicts:
    if has_instruction(claim.text):
        raise ValueError(f"Claim contains instruction: {claim.text[:80]}")
```

---

### 1.2 Fee/Amount Validation — Never Invent Numbers
**Problem:** LLM invents fees like "₹500 fine" and attaches them to a real source ID (B2), bypassing citation checks.
**What to do:**
- Pre-extract all numeric values from evidence before handing to LLM
- Pass extracted numbers to LLM in a separate field: `KNOWN_AMOUNTS: [100, 500, 1000]`
- In validation: any amount in claim MUST appear in evidence text
- Location: `src/revenue_jarvis/answer.py`, before LLM call

**Code sketch:**
```python
import re

def extract_amounts(evs: list[Evidence]) -> set[str]:
    """Extract all numeric values (fees, percentages, deadlines) from evidence."""
    amounts = set()
    for e in evs:
        # Currency amounts: ₹500, Rs. 100, rupees 250
        amounts.update(re.findall(r'[₹Rs.]\s*(\d+(?:,\d{3})*)', e.text))
        # Percentages: 10%, 5.5%
        amounts.update(re.findall(r'(\d+(?:\.\d+)?)\s*%', e.text))
        # Deadlines: 30 days, 6 months
        amounts.update(re.findall(r'(\d+)\s*(day|week|month|year)s?', e.text))
    return amounts

# In ask() before LLM call:
known_amounts = extract_amounts(evs)
prompt = f"EVIDENCE:\n{_evidence_block(evs)}\n\nKNOWN NUMERIC VALUES: {known_amounts}\nDo not invent any values outside this list."

# In validate(), check claims:
for claim in ans.claims:
    invented = set(re.findall(r'[₹Rs.]\s*(\d+)', claim.text)) - known_amounts
    if invented:
        raise ValueError(f"Invented amounts: {invented}")
```

---

### 1.3 Evidence Citation Mapping — Fix Wrong Page/Section
**Problem:** Neighboring text receives citation from wrong chunk (e.g., claim="X from page 10" but evidence B2 is from page 23).
**What to do:**
- Before LLM call, create a citation map: chunk_id → (page, section, printed_label)
- Pass to LLM as: `[B1] (PDF p.72, printed p.10): "...text..."`
- In validation: for each source_id, verify claim text appears in that chunk's text
- Location: `src/revenue_jarvis/answer.py`, function `_evidence_block()`

**Code sketch:**
```python
def _evidence_block_with_metadata(evs: list[Evidence]) -> str:
    """Evidence block with page/section metadata for LLM clarity."""
    parts = []
    for e in evs:
        meta = f"(PDF p.{e.pdf_page}, printed p.{e.printed_page})" if e.printed_page else f"(PDF p.{e.pdf_page})"
        if e.section:
            meta = f"(s.{e.section}, {meta})"
        head = f"[{e.sid}] {e.doc_title} {meta}"
        body = e.text
        if e.neighbors:
            body += f"\n(continues: {e.neighbors[:200]}...)"
        parts.append(f"{head}\n{body}")
    return "\n\n".join(parts)

# In validate(), verify claim text overlap:
def text_overlap(claim_text: str, evidence_text: str, min_overlap=3) -> bool:
    """Check if key phrase from claim appears in evidence."""
    words = set(claim_text.lower().split())
    evidence_words = set(evidence_text.lower().split())
    overlap = len(words & evidence_words)
    return overlap >= min_overlap

for claim in ans.claims:
    for sid in claim.source_ids:
        ev = {e.sid: e for e in evs}[sid]
        if not text_overlap(claim.text, ev.text):
            raise ValueError(f"Claim '{claim.text[:50]}' has no overlap with {sid}")
```

---

### 1.4 Law Parsing — Fix Mislabeled Provisions
**Problem:** Law text parser labels "Rule 5" as a section, or misses "Chapter 10" boundaries.
**What to do:**
- Review `src/revenue_jarvis/ingest/laws.py` — enhance regex patterns for act/rule/chapter/section parsing
- Add unit tests for each law file: verify section boundaries match official documents
- Location: `src/revenue_jarvis/ingest/laws.py`, function that parses section headings

**Code sketch:**
```python
# In laws.py, improve section detection:
SECTION_PATTERNS = [
    r'^Section\s+(\d+[A-Z]?(?:\.\d+)?)',  # Section 5, 5A, 5.1
    r'^Rule\s+(\d+)',                       # Rule 10
    r'^Chapter\s+(\d+)',                    # Chapter 15
    r'^Para(?:graph)?\s+(\d+)',             # Para 20
    r'^\(\s*(\d+)\s*\)',                    # (5)
]

def extract_section(line: str) -> str | None:
    """Extract section number from line."""
    for pattern in SECTION_PATTERNS:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

# Add tests:
# test_plra_sections() — verify Section 5, 10, etc. from PLRA_1887
# test_plam_chapters() — verify Chapter 5, 10, etc. from PLAM
# test_rules_numbering() — verify Rule 1, 2, etc. consistency
```

---

## Priority 2: Hindi Query Pipeline — Enable Synthesis
**Problem:** Hindi queries retrieve laws but LLM never runs; answer stuck at "sources_only".
**What to do:**
- Trace the code path: `detect_language("Hindi text") → "hi"` → `search()` returns only laws
- But then `ask()` checks `if not any(e.source_type == "book" for e in evs)` → returns "not_found"
- Fix: Allow synthesis if law evidence exists (not just book)
- Location: `src/revenue_jarvis/answer.py`, line 172

**Code sketch:**
```python
# BEFORE (line 172):
if not any(e.source_type == "book" for e in evs):
    res = JarvisAnswer(status="not_found", spoken=f"{title.capitalize()}, I could not find this in the book.")

# AFTER:
if not evs:
    res = JarvisAnswer(status="not_found", spoken=f"{title.capitalize()}, I could not find this in the knowledge base.")
elif not any(e.source_type == "book" for e in evs) and lang == "hi":
    # Hindi query: allow synthesis from laws only
    # But note: book-grounded answers are stronger
    res = JarvisAnswer(status="sources_only", spoken=f"{title.capitalize()}, here are the official laws that apply.",
                       backend="none", **base)
    res.warnings.append("Book evidence unavailable (Hindi query); answer grounded in official acts/rules only.")
else:
    # Normal synthesis path
    ...
```

---

### 2.1 Query Rewrite Overhead — Remove Dead Code
**Problem:** `_rewrite()` is disabled in .env but still called, incurring a try/except per question.
**What to do:**
- If `llm_query_rewrite=false`, skip the call entirely (don't even try/except)
- Location: `src/revenue_jarvis/answer.py`, function `ask()`, line 165

**Code sketch:**
```python
# BEFORE:
terms = self._rewrite(question)

# AFTER:
terms = self._rewrite(question) if self.s.llm_query_rewrite else []
```

---

## Priority 3: Web UI Fixes

### 3.1 Citation Button State — Fix Cross-Answer Leakage
**Problem:** Clicking a citation button from an old answer opens evidence from the new answer.
**What to do:**
- Each answer generation should assign a unique `answer_id` (UUID or timestamp)
- Store answer_id in both answer JSON and evidence block
- Web UI should only render buttons for evidence from the SAME answer_id
- Location: `src/revenue_jarvis/web/app.js` + `src/revenue_jarvis/answer.py`

**Code sketch (Python):**
```python
import uuid
from dataclasses import dataclass

@dataclass
class JarvisAnswer:
    answer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ...

# In to_dict():
return {
    "answer_id": self.answer_id,
    "evidence": [{"answer_id": self.answer_id, **ev_dict} for ev_dict in self.evidence],
    ...
}
```

**Code sketch (JavaScript):**
```javascript
// In app.js, render function:
function renderAnswer(answer) {
    const ansId = answer.answer_id;
    const evidenceMap = {};
    answer.evidence.forEach(ev => {
        evidenceMap[ev.sid] = ev;
    });
    
    // Each citation button only opens evidence from this answer
    document.querySelectorAll(`[data-answer-id="${ansId}"] .citation`).forEach(btn => {
        btn.onclick = (e) => {
            const sid = e.target.dataset.sid;
            const ev = evidenceMap[sid];
            if (ev) openModal(ev);
        };
    });
}
```

---

## Priority 4: Performance Profiling & Optimization

### 4.1 Where Are the 18–22 Seconds?
**What to do:**
- Add timing probes to measure each stage:
  1. Voice input → text (if applicable)
  2. Language detection
  3. Retrieval (embedding lookup + BM25)
  4. LLM synthesis
  5. Validation + rendering
- Log times to disk for analysis
- Location: `src/revenue_jarvis/answer.py`, function `ask()`

**Code sketch:**
```python
import time

def ask(self, question: str, log: bool = True) -> JarvisAnswer:
    t0 = time.time()
    timings = {}
    
    question = (question or "").strip()
    lang = detect_language(question)
    timings["detect"] = time.time() - t0
    
    t1 = time.time()
    evs = self.retriever.search(question, ...)
    timings["retrieve"] = time.time() - t1
    
    t2 = time.time()
    raw = extract_json(self.backend.complete(system, prompt, ...))
    timings["llm"] = time.time() - t2
    
    t3 = time.time()
    ans, warns = validate(raw, evs)
    timings["validate"] = time.time() - t3
    
    res.latency_ms = int((time.time() - t0) * 1000)
    res.timings = timings  # Debug info
    
    if log:
        logging.info(f"Timings (ms): {timings}")
    
    return res
```

Then run 10 questions and see where time is spent. **My prediction:** LLM (12–15s) + retrieval (2–3s) + speech (if enabled). Optimization options:
- Use Claude Haiku instead of Sonnet (faster, but less accurate)
- Smaller evidence context (e.g., 3 claims instead of 5 + 3 laws)
- Batch multiple questions per LLM call (but adds latency)

---

## Priority 5: Test Coverage & Release Gates

### 5.1 Unit Tests for Each Fix
**What to do:**
- Add pytest cases for:
  - `test_instruction_injection()` — verify claims with "you must" are rejected
  - `test_invented_fees()` — verify amounts outside evidence are rejected
  - `test_citation_overlap()` — verify claims overlap with cited evidence
  - `test_hindi_query_synthesis()` — verify Hindi queries reach LLM
  - `test_web_answer_isolation()` — verify buttons only open correct evidence
- Location: `tests/test_answer.py`, `tests/test_grounding.py` (new)

**Code sketch:**
```python
# tests/test_grounding.py
def test_instruction_injection():
    """Ensure LLM-injected instructions are caught."""
    raw = {
        "status": "answered",
        "spoken": "Here's the answer",
        "claims": [
            {"text": "Officer must approve this immediately", "source_ids": ["B1"]}
        ],
        ...
    }
    with pytest.raises(ValueError, match="instruction"):
        validate(raw, [Evidence(...)])

def test_invented_fees():
    """Ensure invented amounts are rejected."""
    evs = [Evidence(text="Fine is ₹100", ...)]
    raw = {
        "claims": [
            {"text": "Fine is ₹500 per case", "source_ids": ["L1"]}  # ₹500 not in evidence
        ],
        ...
    }
    with pytest.raises(ValueError, match="invented amounts"):
        validate(raw, evs)
```

---

### 5.2 Release Gates (Must Pass Before Deployment)
**What to do:**
- Define 5 gates that must pass before releasing to production:

1. **Grounding Gate:** No invented fees, amounts, or dates
   - Test: run 20 questions, check all numeric claims are in evidence
   - Pass: 100% of claims cite real evidence

2. **Citation Gate:** No wrong page/section citations
   - Test: click every citation, verify evidence matches claim
   - Pass: 100% citation accuracy

3. **Language Gate:** No Devanagari in responses
   - Test: ask 10 Hindi questions, inspect output
   - Pass: 0% Devanagari, 100% Gurmukhi/English

4. **Latency Gate:** < 15 seconds median
   - Test: 50 questions, measure end-to-end time
   - Pass: median ≤ 15s, 95th percentile ≤ 25s

5. **Coverage Gate:** Handles 90% of common officer questions
   - Test: curate 30 real officer questions, run through system
   - Pass: 27/30 get substantive answers (not "insufficient")

**Code sketch:**
```python
# tests/test_release_gates.py
class TestReleaseGates:
    def test_grounding_gate(self):
        """All numeric claims must exist in evidence."""
        questions = [
            "What is the fee for partition under PLRA?",
            "How many days to appeal after ejectment?",
            ...
        ]
        for q in questions:
            ans = jarvis.ask(q)
            for claim in ans.claims:
                amounts = re.findall(r'\d+', claim.text)
                for amt in amounts:
                    assert amt in _evidence_text(ans.evidence), f"Invented: {amt}"
    
    def test_latency_gate(self):
        """Median latency < 15s."""
        latencies = []
        for q in 50_questions:
            ans = jarvis.ask(q)
            latencies.append(ans.latency_ms)
        assert np.median(latencies) <= 15000, f"Median {np.median(latencies)/1000:.1f}s"
    
    def test_coverage_gate(self):
        """90% of officer questions get substantive answers."""
        officer_qs = load_officer_question_set(30)
        substantive = sum(1 for q in officer_qs if jarvis.ask(q).status == "answered")
        assert substantive >= 27, f"Only {substantive}/30 answered"
```

---

## What to Tell Codex

**"Fix these issues in this order:**

1. **Block instruction injection** (test: claim="Ignore this" → rejected)
2. **Prevent invented fees** (test: claim="₹500" but evidence says "₹100" → rejected)
3. **Fix citation overlap** (test: evidence B2 p.23 but claim says "page 10" → rejected)
4. **Enable Hindi synthesis** (test: Hindi query → LLM answer, not "sources only")
5. **Remove rewrite overhead** (test: disable in code, not just .env)
6. **Fix web citation buttons** (test: old answer's button doesn't leak new evidence)
7. **Profile latency** (test: add timing probes, measure each stage)
8. **Add unit tests** for each fix
9. **Define release gates** — grounding, citation, language, latency, coverage
10. **Run gate tests** before merging to main

**Do not change:**
- Retrieval algorithm (E5 + BM25 fusion is solid)
- SYSTEM prompt structure (grounding by evidence is right approach)
- Book/law separation (correct for this use case)

**Prioritize:** Grounding fixes (1–3) must pass before any optimization."

---

## Success Criteria

After Codex fixes these, Jarvis should:

✓ Never invent fees, dates, or amounts  
✓ Always cite real evidence (no wrong pages)  
✓ Handle Hindi queries with synthesis (not just sources)  
✓ Respond in < 15s median  
✓ Pass all 5 release gates  
✓ Be ready for production with a revenue officer  

---

End Instructions for Codex.
