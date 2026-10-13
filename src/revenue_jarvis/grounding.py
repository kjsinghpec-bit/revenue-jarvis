"""Conservative deterministic support checks; these do not prove semantic entailment."""
from __future__ import annotations

import re
from decimal import Decimal

from .text import GURMUKHI, ascii_digits, nfc, tokenize
from .xref import ACT_HINTS

# Danda/double danda are shared Indic punctuation used in Punjabi too.
FORBIDDEN_SCRIPT = re.compile(r"[\u0900-\u0963\u0966-\u097f\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")
INSTRUCTIONS = re.compile(
    r"\b(?:ignore|skip|disregard|override)\s+(?:this|that|all|previous|the\s+(?:rules|instructions|validation))\b"
    r"|\b(?:you|jarvis|the system)\s+(?:must|should|will|can|cannot)\b"
    r"|\b(?:must|should)\b.{0,60}\b(?:approve|sanction|pay|execute)\b.{0,60}\b(?:now|immediately)\b"
    r"|\b(?:run|execute|write|delete|send)\b.{0,25}\b(?:command|script|file|email|shell|bash)\b"
    r"|(?:ਹਦਾਇਤਾਂ|ਨਿਯਮਾਂ).{0,25}(?:ਅਣਡਿੱਠ|ਨਜ਼ਰਅੰਦਾਜ਼)", re.I,
)
NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"
UNITS = {"day": "day", "days": "day", "ਦਿਨ": "day", "week": "week", "weeks": "week", "ਹਫ਼ਤੇ": "week",
         "month": "month", "months": "month", "ਮਹੀਨੇ": "month", "ਮਹੀਨਾ": "month",
         "year": "year", "years": "year", "ਸਾਲ": "year", "%": "percent", "percent": "percent", "ਫ਼ੀਸਦੀ": "percent"}
SMALL = dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(), range(20)))
SMALL.update(dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10))))
WORD_NUMBERS = re.compile(r"\b(?:" + "|".join(SMALL) + r"|hundred|thousand|lakh|million)(?:[ -]+(?:" + "|".join(SMALL) + r"|hundred|thousand|lakh|million|and))*\b", re.I)
PUNJABI_NUMBERS = dict(zip(
    ('ਇੱਕ', 'ਦੋ', 'ਤਿੰਨ', 'ਚਾਰ', 'ਪੰਜ', 'ਛੇ', 'ਸੱਤ', 'ਅੱਠ', 'ਨੌਂ', 'ਦਸ'),
    range(1, 11),
))
# Python word boundaries split Indic combining marks. Match whole Gurmukhi
# tokens instead, so ਪੰਜ never supplies a value for ਪੰਜਾਹ.
PUNJABI_NUMBER_PATTERN = re.compile(
    r'(?<![\w\u0a00-\u0a7f])(?:' + '|'.join(PUNJABI_NUMBERS) + r')(?![\w\u0a00-\u0a7f])'
)
REVENUE_UNITS = {
    'inch': 'inch', 'inches': 'inch', 'ਇੰਚ': 'inch',
    'centimeter': 'centimeter', 'centimeters': 'centimeter',
    'centimetre': 'centimeter', 'centimetres': 'centimeter', 'ਸੈਂਟੀਮੀਟਰ': 'centimeter',
    'foot': 'foot', 'feet': 'foot', 'ਫੁੱਟ': 'foot',
    'meter': 'meter', 'meters': 'meter', 'metre': 'meter', 'metres': 'meter', 'ਮੀਟਰ': 'meter',
    'kanal': 'kanal', 'kanals': 'kanal', 'ਕਨਾਲ': 'kanal',
    'marla': 'marla', 'marlas': 'marla', 'ਮਰਲਾ': 'marla', 'ਮਰਲੇ': 'marla',
    'times': 'multiplier', 'ਗੁਣਾ': 'multiplier', '×': 'multiplier',
}
REVENUE_UNIT_PATTERN = re.compile(
    '(' + NUMBER + r')\s*(' + '|'.join(
        re.escape(unit) for unit in sorted(REVENUE_UNITS, key=len, reverse=True)
    ) + r')(?![\w\u0a00-\u0a7f])'
)

NEGATIVE = r"\b(?:not|cannot|never|prohibited)\b|ਨਹੀਂ|ਮਨਾਹੀ"
ROLES = {
    'assistant_collector': r'\bassistant\s+collector\b|ਸਹਾਇਕ\s+(?:ਕਲੈਕਟਰ|ਕੁਲੈਕਟਰ)',
    'naib_tehsildar': r'\bnaib\s+(?:tehsildar|tahsildar)\b|ਨਾਇਬ\s+ਤਹਿਸੀਲਦਾਰ',
    'financial_commissioner': r'\bfinancial\s+commissioner\b|ਵਿੱਤ\s+ਕਮਿਸ਼ਨਰ',
    'district_revenue_officer': r'\bdistrict\s+revenue\s+officer\b|ਜ਼ਿਲ੍ਹਾ\s+ਮਾਲ\s+ਅਫ਼ਸਰ',
    'revenue_officer': r'\brevenue\s+officer\b|ਮਾਲ\s+ਅਫ਼ਸਰ',
    'patwari': r'\bpatwari\b|ਪਟਵਾਰੀ',
    'kanungo': r'\bkanungo\b|ਕਾਨੂੰਗੋ',
    'tehsildar': r'\b(?:tehsildar|tahsildar)\b|ਤਹਿਸੀਲਦਾਰ',
    'collector': r'\bcollector\b|ਕੁਲੈਕਟਰ|ਕਲੈਕਟਰ',
    'commissioner': r'\bcommissioner\b|ਕਮਿਸ਼ਨਰ',
}
ACTIONS = {
    'approve': r'\bapprov\w*\b|ਮਨਜ਼ੂਰ|ਮੰਜੂਰ',
    'partition': r'\bpartition\w*\b|ਤਕਸੀਮ',
    'eject': r'\b(?:eject|evict)\w*\b|ਬੇਦਖ਼ਲ|ਬੇਦਖਲ',
    'demarcate': r'\bdemarcat\w*\b|ਨਿਸ਼ਾਨਦੇਹੀ|ਨਿਸ਼ਾਨਦਿਹੀ',
}


def clauses(text: str) -> list[str]:
    # Keep decimal/currency periods intact; split independent coordinated clauses.
    return [x.strip() for x in re.split(r'(?<=[.!?।])\s+(?!\d)|[;\n]+|\s+(?:and|but|ਅਤੇ|ਪਰ)\s+(?=(?:the\s+)?(?:fee|fine|collector|tehsildar|patwari|commissioner|ਫ਼ੀਸ|ਫੀਸ|ਜੁਰਮਾਨਾ|ਕਲੈਕਟਰ|ਕੁਲੈਕਟਰ|ਤਹਿਸੀਲਦਾਰ|ਪਟਵਾਰੀ))', normalize(text)) if x.strip()]


def authority_frames(text: str) -> list[tuple[str, str, bool, str]]:
    """Limited officer/action clause matching, not a general legal entailment model."""
    frames = []
    for clause in clauses(text):
        roles, occupied = [], []
        for name, pattern in ROLES.items():
            for m in re.finditer(pattern, clause):
                if not any(a <= m.start() < b for a,b in occupied):
                    roles.append((m.start(), name))
                    occupied.append(m.span())
        for action, pattern in ACTIONS.items():
            for match in re.finditer(pattern, clause):
                if not roles:
                    continue
                before = [r for r in roles if r[0] <= match.start()]
                role = max(before)[1] if before else min(roles)[1]
                frames.append((role, action, bool(re.search(NEGATIVE, clause)), clause))
    return frames


def contradictory_claims(texts: list[str]) -> bool:
    stop = {'the', 'a', 'an', 'may', 'must', 'can', 'cannot', 'not', 'shall', 'should', 'is', 'be'}
    seen = {}
    for text in texts:
        for role, action, negative, clause in authority_frames(text):
            remaining = re.sub(ROLES[role], ' ', clause)
            remaining = re.sub(ACTIONS[action], ' ', remaining)
            key = (role, action, tuple(sorted(set(tokenize(remaining)) - stop)))
            if key in seen and seen[key] != negative:
                return True
            seen[key] = negative
    numeric_seen = {}
    for text in texts:
        # Only compare identical textual scopes after stripping amounts/units.
        # Different proceedings or conditions must not be conflated.
        scope = _numeric_text(text)
        scope = re.sub(r'(?:₹|\brs\.?|\binr\b|\brupees?\b)|' + NUMBER, ' ', scope)
        scope = tuple(sorted(set(tokenize(scope)) - stop))
        amounts = numeric_facts(text)
        for kind in ('fee', 'fine'):
            values = {value for label, value in amounts if label == kind}
            if len(values) != 1:
                continue  # multi-component claims need contextual audit, not a false conflict
            value = next(iter(values))
            key = (kind, scope)
            if key in numeric_seen and numeric_seen[key] != value:
                return True
            numeric_seen[key] = value
    return False


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", ascii_digits(nfc(text))).strip().casefold()


def has_instruction(text: str) -> bool:
    return bool(INSTRUCTIONS.search(text))


def _numeric_text(text: str) -> str:
    def replace(m):
        total = current = 0
        for word in re.split(r"[ -]+", m.group().lower()):
            if word in SMALL:
                current += SMALL[word]
            elif word == "hundred":
                current = max(1, current) * 100
            elif word in {"thousand", "lakh", "million"}:
                total += max(1, current) * {"thousand": 1000, "lakh": 100000, "million": 1000000}[word]
                current = 0
        return str(total + current)
    text = WORD_NUMBERS.sub(replace, normalize(text))
    return PUNJABI_NUMBER_PATTERN.sub(lambda m: str(PUNJABI_NUMBERS[m.group()]), text)


def numeric_facts(text: str) -> set[tuple[str, str]]:
    """Exact atoms and typed amounts, durations, dates and revenue units.

    Unit conversions and compound Punjabi number phrases are not inferred.
    """
    text = _numeric_text(text)
    value = lambda s: format(Decimal(s.replace(",", "")).normalize(), 'f')
    facts = {("number", value(m.group())) for m in re.finditer(NUMBER, text)}
    for m in re.finditer(r"(?:₹|\brs\.?|\binr\b|\brupees?\b)\s*(" + NUMBER + r")|(" + NUMBER + r")\s*(?:rupees?\b|ਰੁਪਏ|ਰੁਪੈ|ਰੁਪਇਆ)", text):
        facts.add(("currency", value(m.group(1) or m.group(2))))
    for m in re.finditer(r"(" + NUMBER + r")\s*(%|\b(?:days?|weeks?|months?|years?|percent)\b|ਦਿਨ|ਹਫ਼ਤੇ|ਮਹੀਨੇ|ਮਹੀਨਾ|ਸਾਲ|ਫ਼ੀਸਦੀ)", text):
        facts.add((UNITS[m.group(2)], value(m.group(1))))
    for m in REVENUE_UNIT_PATTERN.finditer(text):
        facts.add((REVENUE_UNITS[m.group(2)], value(m.group(1))))
    for clause in clauses(text):
        for topic, pattern in (('appeal', r'\bappeal\w*\b|ਅਪੀਲ'), ('revision', r'\brevision\w*\b|ਰਿਵੀਜ਼ਨ')):
            if re.search(pattern, clause):
                for m in re.finditer('(' + NUMBER + r')\s*(\b(?:days?|weeks?|months?|years?)\b|ਦਿਨ|ਹਫ਼ਤੇ|ਮਹੀਨੇ|ਮਹੀਨਾ|ਸਾਲ)', clause):
                    facts.add((topic + ':' + UNITS[m.group(2)], value(m.group(1))))
    for m in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b|\b\d{1,2}\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b", text):
        facts.add(("date", m.group()))
    for sentence in clauses(text):
        labels = [(m.start(), label) for label, pattern in (('fee', r'\bfees?\b|ਫ਼ੀਸ|ਫੀਸ'), ('fine', r'\bfines?\b|ਜੁਰਮਾਨਾ')) for m in re.finditer(pattern, sentence)]
        for label, pattern in (("fee", r"\bfees?\b|ਫ਼ੀਸ|ਫੀਸ"), ("fine", r"\bfines?\b|ਜੁਰਮਾਨਾ")):
            if re.search(pattern, sentence):
                for m in re.finditer(r"(?:₹|\brs\.?|\binr\b|\brupees?\b)\s*(" + NUMBER + r")|(" + NUMBER + r")\s*(?:rupees?\b|ਰੁਪਏ|ਰੁਪੈ|ਰੁਪਇਆ)", sentence):
                    preceding = [(position, name) for position, name in labels if position <= m.start()]
                    if preceding and max(preceding)[1] == label:
                        facts.add((label, value(m.group(1) or m.group(2))))
                # Bare amounts must not borrow a page/section number from metadata.
                for m in re.finditer('(?:' + pattern + r')\s*(?:is|are|of|:|=)?\s*(' + NUMBER + ')', sentence):
                    facts.add((label, value(m.group(1))))
    return facts


def check_generated(text: str) -> None:
    if FORBIDDEN_SCRIPT.search(text):
        raise ValueError("Unsupported output script")
    if has_instruction(text):
        raise ValueError("Claim contains unsupported instruction")


def check_support(text: str, quotes: list[str], evidence: list) -> None:
    """Fail closed on unsupported numbers/units, explicit locators and role changes."""
    supported = set().union(*(numeric_facts(q) for q in quotes)) if quotes else set()
    numeric_text = ascii_digits(text)
    spans = []
    # Validate and mask only explicit locator occurrences. Metadata numbers must
    # not become counts, amounts or durations elsewhere in the same claim.
    for m in re.finditer(r"\b(?:(PDF|Book)\s+)?(?:p\.?|page)\s*(\d+)\b", numeric_text, re.I):
        pages = {str(e.pdf_page) for e in evidence}
        if (m.group(1) or '').lower() == 'book':
            pages = {str(e.printed_page) for e in evidence if e.printed_page}
        elif (m.group(1) or '').lower() != 'pdf':
            pages |= {str(e.printed_page) for e in evidence if e.printed_page}
        if m.group(2) not in pages:
            raise ValueError("Claim cites the wrong page")
        spans.append(m.span(2))
    locator = re.compile(r'(?<!\w)(sections?|s\.|rules?|r\.|para(?:graph)?|ਧਾਰਾ(?:ਵਾਂ)?|ਨਿਯਮ|ਪੈਰਾ)\s*(\d+(?:\.\d+)?(?:-?[A-Z])?)', re.I)
    def locator_key(match):
        unit = match.group(1).lower()
        kind = 'rule' if unit.startswith('r') or unit == 'ਨਿਯਮ' else 'paragraph' if unit.startswith('p') or unit == 'ਪੈਰਾ' else 'section'
        return kind, match.group(2).upper().replace('-', '')
    known_locators = {locator_key(m) for q in quotes for m in locator.finditer(ascii_digits(q))}
    for e in evidence:
        if e.source_type == 'book':
            # Book chunks have page metadata, not structured section metadata.
            known_locators |= {locator_key(m) for m in locator.finditer(ascii_digits(e.text))}
    for m in locator.finditer(numeric_text):
        kind, number = locator_key(m)
        if (kind, number) not in known_locators and not any(e.section and str(e.section).upper().replace('-', '') == number
                   and (not e.provision_kind or e.provision_kind == kind) for e in evidence):
            raise ValueError("Claim cites the wrong section/rule/paragraph")
        spans.append(m.span(2))
    # A source-verified year inside an instrument's NAME is a locator, not an
    # amount/date asserted by this claim. Mask only that occurrence; another
    # occurrence as a fee or deadline must still pass the normal checks.
    instrument_titles = []
    for pattern, name in ACT_HINTS:
        year = re.search(r"\b\d{4}\b", name)
        if not year:
            continue
        for mention in re.finditer(pattern, numeric_text, re.I):
            suffix = re.match(r"[\s,(\-]*?(" + year.group() + r")\b", numeric_text[mention.end():])
            if not suffix:
                continue
            matching = [e for e in evidence if re.search(pattern, " ".join((e.doc_title or "", e.short_name or "", e.text)), re.I)
                        and re.search(r"\b" + year.group() + r"\b", ascii_digits(" ".join((e.doc_title or "", e.short_name or "", e.text))))]
            if matching:
                spans.append((mention.end() + suffix.start(1), mention.end() + suffix.end(1)))
                instrument_titles.extend(e.doc_title for e in matching if e.doc_title)
    for start, end in sorted(set(spans), reverse=True):
        numeric_text = numeric_text[:start] + " " * (end - start) + numeric_text[end:]
    missing = numeric_facts(numeric_text) - supported
    if missing:
        raise ValueError(f"Unsupported numeric amount/date/unit: {sorted(missing)}")
    source = normalize(" ".join(quotes))
    lexical_source = normalize(" ".join([*quotes, *instrument_titles]))
    claim = normalize(text)
    if bool(GURMUKHI.search(claim)) == bool(GURMUKHI.search(source)):
        stop = {"a", "an", "the", "is", "are", "any", "for", "to", "of", "in", "may", "must", "can", "shall", "should", "be", "under", "and", "or"}
        content = set(tokenize(claim)) - stop
        if not content or len(content & set(tokenize(lexical_source))) / len(content) < 0.5:
            raise ValueError("Claim has insufficient textual overlap with supporting quote")
    # Cross-script claims require exact source quotes and the checks below;
    # word overlap is inapplicable. Their translation/entailment needs audit.
    concepts = [r"\bpatwari\b|ਪਟਵਾਰੀ", r"\btehsildar\b|\btahsildar\b|ਤਹਿਸੀਲਦਾਰ", r"\bcollector\b|ਕੁਲੈਕਟਰ|ਕਲੈਕਟਰ",
                r"\bfee\b|\bfees\b|ਫ਼ੀਸ|ਫੀਸ", r"\bfine\b|ਜੁਰਮਾਨਾ"]
    for pattern in concepts:
        if re.search(pattern, claim) and not re.search(pattern, source):
            raise ValueError("Claim role or amount context is not supported by its quote")
    # Conservative polarity/modality checks. Translation and complex entailment
    # still require audit; do not label these checks a correctness probability.
    frames = authority_frames(claim)
    source_frames = [frame for q in quotes for frame in authority_frames(q)]
    scoped = []
    for role, action, negative, _ in frames:
        matches = [frame for frame in source_frames if frame[0] == role and frame[1] == action]
        if not matches:
            raise ValueError('Claim officer authority is not supported by a source clause')
        matches = [frame for frame in matches if frame[2] == negative]
        if not matches:
            raise ValueError('Claim authority negation differs from supporting text')
        scoped.extend(frame[3] for frame in matches)
    polarity_source = ' '.join(scoped) if frames else source
    if bool(re.search(NEGATIVE, claim)) != bool(re.search(NEGATIVE, polarity_source)):
        raise ValueError("Claim negation differs from supporting text")
    if re.search(r"\b(?:must|shall|required)\b|ਲਾਜ਼ਮੀ", claim) and re.search(r"\bmay\b|ਸਕਦਾ", polarity_source) and not re.search(r"\b(?:must|shall|required)\b|ਲਾਜ਼ਮੀ", polarity_source):
        raise ValueError("Claim changes permission into a requirement")
