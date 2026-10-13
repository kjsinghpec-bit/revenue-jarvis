"""Unicode-safe normalisation, tokenisation, language detection and search aliases.

Rules: never "spell-correct" legal text. Only NFC + whitespace + obvious OCR
noise lines are cleaned; the raw OCR is always kept alongside.
"""
from __future__ import annotations

import re
import unicodedata

GURMUKHI = re.compile(r"[\u0A00-\u0A7F]")
DEVANAGARI = re.compile(r"[\u0900-\u097F]")
LATIN = re.compile(r"[A-Za-z]")
TOKEN = re.compile(r"[0-9A-Za-z\u0A00-\u0A7F\u0900-\u097F]+")
NOISE_LINE = re.compile(r"^[\s|=\-_~.,:;'\"`!@#$%^&*()+<>/\\\[\]{}SsOo0-]{0,}$")
_GURMUKHI_DIGITS = str.maketrans("੦੧੨੩੪੫੬੭੮੯", "0123456789")
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def clean_ocr(text: str) -> str:
    """Safe cleanup only: NFC, collapse spaces, drop pure-noise lines, strip stray leading pipes."""
    out = []
    for ln in nfc(text).splitlines():
        ln = re.sub(r"^\s*[|]\s*", "", ln)
        ln = re.sub(r"\s+", " ", ln).strip()
        if not ln:
            continue
        if NOISE_LINE.fullmatch(ln) and not re.search(r"\d", ln):
            continue
        if len(GURMUKHI.findall(ln)) + len(LATIN.findall(ln)) + len(re.findall(r"\d", ln)) < 2:
            continue
        out.append(ln)
    return "\n".join(out)


def ascii_digits(s: str) -> str:
    return s.translate(_GURMUKHI_DIGITS).translate(_DEVANAGARI_DIGITS)


def devanagari_to_gurmukhi(s: str) -> str:
    """DEPRECATED: Naive phonetic conversion is unreliable for legal terms.
    This function is kept for backward compatibility but should NOT be used for RAG retrieval.
    Use the ALIASES dict instead for accurate terminology mapping."""
    out = []
    for ch in s:
        cp = ord(ch)
        if 0x0905 <= cp <= 0x0963:
            g = chr(cp + 0x100)
            out.append(g if unicodedata.name(g, "") else ch)
        else:
            out.append(ch)
    return "".join(out)


def tokenize(s: str) -> list[str]:
    s = ascii_digits(nfc(s)).lower()
    return TOKEN.findall(s)


def detect_language(s: str) -> str:
    """'pa' Gurmukhi, 'hi' Devanagari, 'en' English, 'hinglish' romanised Hindi/Punjabi."""
    g, d, l_ = len(GURMUKHI.findall(s)), len(DEVANAGARI.findall(s)), len(LATIN.findall(s))
    if g >= max(d, 1) and g >= l_ * 0.3:
        return "pa"
    if d >= max(g, 1) and d >= l_ * 0.3:
        return "hi"
    words = set(tokenize(s))
    roman = {"kya", "hai", "kaise", "kaun", "kis", "ki", "ka", "ke", "ko", "nu", "da", "di", "de", "kidan",
             "hunda", "hundi", "karna", "kariye", "kithe", "kado", "kab", "batao", "dasso", "chahida", "hota"}
    if len(words & roman) >= 2:
        return "hinglish"
    return "en"


# Reviewed search aliases: English / Hindi / romanised -> the book's Gurmukhi terms.
# Used ONLY to widen the keyword search, never to change source text.
ALIASES: dict[str, list[str]] = {
    "partition": ["ਤਕਸੀਮ", "ਵੰਡ", "ਤਕਸੀਮ ਜ਼ਮੀਨ"],
    "takseem": ["ਤਕਸੀਮ"], "batwara": ["ਤਕਸੀਮ", "ਵੰਡ"], "बंटवारा": ["ਤਕਸੀਮ", "ਵੰਡ"], "बंटवारे": ["ਤਕਸੀਮ", "ਵੰਡ"], "तकसीम": ["ਤਕਸੀਮ"],
    "consolidation": ["ਮੁਰੱਬਾਬੰਦੀ", "ਚੱਕਬੰਦੀ", "ਮੁਰੱਬੇਬੰਦੀ"], "chakbandi": ["ਚੱਕਬੰਦੀ", "ਮੁਰੱਬਾਬੰਦੀ"],
    "murabbabandi": ["ਮੁਰੱਬਾਬੰਦੀ"], "चकबंदी": ["ਚੱਕਬੰਦੀ", "ਮੁਰੱਬਾਬੰਦੀ"],
    "mutation": ["ਇੰਤਕਾਲ"], "intkal": ["ਇੰਤਕਾਲ"], "inteqal": ["ਇੰਤਕਾਲ"], "इंतकाल": ["ਇੰਤਕਾਲ"],
    "musanna": ["ਮੁਸੰਨਾ"], "duplicate": ["ਮੁਸੰਨਾ"], "lost": ["ਗੁੰਮ"],
    "demarcation": ["ਨਿਸ਼ਾਨਦੇਹੀ"], "nishandehi": ["ਨਿਸ਼ਾਨਦੇਹੀ"], "निशानदेही": ["ਨਿਸ਼ਾਨਦੇਹੀ"],
    "girdawari": ["ਗਿਰਦਾਵਰੀ"], "गिरदावरी": ["ਗਿਰਦਾਵਰੀ"], "khasra": ["ਖਸਰਾ"],
    "jamabandi": ["ਜਮ੍ਹਾਂਬੰਦੀ", "ਜਮਾਂਬੰਦੀ"], "जमाबंदी": ["ਜਮ੍ਹਾਂਬੰਦੀ"],
    "shamlat": ["ਸ਼ਾਮਲਾਤ"], "शामलात": ["ਸ਼ਾਮਲਾਤ"], "common": ["ਸ਼ਾਮਲਾਤ", "ਸਾਂਝੀ"],
    "panchayat": ["ਪੰਚਾਇਤ", "ਪੰਚਾਇਤੀ"], "पंचायत": ["ਪੰਚਾਇਤ"],
    "ejectment": ["ਬੇਦਖ਼ਲੀ", "ਬੇਦਖਲੀ"], "eviction": ["ਬੇਦਖ਼ਲੀ", "ਬੇਦਖਲੀ"], "बेदखली": ["ਬੇਦਖ਼ਲੀ"],
    "will": ["ਵਸੀਅਤ"], "wasiyat": ["ਵਸੀਅਤ"], "वसीयत": ["ਵਸੀਅਤ"],
    "inheritance": ["ਵਿਰਾਸਤ", "ਵਾਰਸ"], "succession": ["ਵਿਰਾਸਤ", "ਵਾਰਸ"], "virasat": ["ਵਿਰਾਸਤ"],
    "विरासत": ["ਵਿਰਾਸਤ"], "heir": ["ਵਾਰਸ"],
    "registration": ["ਰਜਿਸਟਰੀ", "ਰਜਿਸਟਰ"], "registry": ["ਰਜਿਸਟਰੀ"], "रजिस्ट्री": ["ਰਜਿਸਟਰੀ"],
    "deed": ["ਦਸਤਾਵੇਜ਼", "ਵਸੀਕਾ"], "document": ["ਦਸਤਾਵੇਜ਼", "ਵਸੀਕਾ"],
    "stamp": ["ਅਸ਼ਟਾਮ", "ਸਟੈਂਪ"], "स्टाम्प": ["ਅਸ਼ਟਾਮ"],
    "acquisition": ["ਐਕਵਾਇਰ", "ਅਕਵਾਇਰ", "ਐਕੁਆਇਰ", "ਗ੍ਰਹਿਣ"], "acquire": ["ਐਕਵਾਇਰ", "ਐਕੁਆਇਰ"],
    "compensation": ["ਮੁਆਵਜ਼ਾ", "ਮੁਆਵਜਾ"], "muavza": ["ਮੁਆਵਜ਼ਾ"], "मुआवजा": ["ਮੁਆਵਜ਼ਾ"],
    "price": ["ਕੀਮਤ", "ਰੇਟ", "ਮੁੱਲ"], "rate": ["ਰੇਟ", "ਕੀਮਤ"], "collector": ["ਕੁਲੈਕਟਰ", "ਕਲੈਕਟਰ"],
    "attorney": ["ਮੁਖ਼ਤਿਆਰਨਾਮਾ", "ਮੁਖਤਿਆਰਨਾਮਾ", "ਮੁਖ਼ਤਾਰਨਾਮਾ"], "mukhtiarnama": ["ਮੁਖ਼ਤਿਆਰਨਾਮਾ"],
    "appeal": ["ਅਪੀਲ"], "revision": ["ਨਿਗਰਾਨੀ", "ਰਵੀਜ਼ਨ"], "review": ["ਨਜ਼ਰਸਾਨੀ", "ਰਿਵਿਊ"],
    "abadi": ["ਆਬਾਦੀ"], "deh": ["ਦੇਹ"], "fard": ["ਫ਼ਰਦ", "ਫਰਦ"], "badar": ["ਬਦਰ"],
    "court": ["ਅਦਾਲਤ"], "revenue": ["ਮਾਲ"], "officer": ["ਅਧਿਕਾਰੀ", "ਅਫ਼ਸਰ"],
    "patwari": ["ਪਟਵਾਰੀ"], "kanungo": ["ਕਾਨੂੰਗੋ"], "tehsildar": ["ਤਹਿਸੀਲਦਾਰ"], "collector's": ["ਕੁਲੈਕਟਰ"],
    "ownership": ["ਮਾਲਕੀ", "ਮਾਲਕ"], "owner": ["ਮਾਲਕ"], "cultivation": ["ਕਾਸ਼ਤ", "ਕਾਸ਼ਤਕਾਰ"],
    "tenant": ["ਮੁਜ਼ਾਰਾ", "ਕਾਸ਼ਤਕਾਰ"], "mortgage": ["ਰਹਿਨ", "ਗਹਿਣੇ"],
    "refusal": ["ਇਨਕਾਰ"], "refuse": ["ਇਨਕਾਰ"], "glossary": ["ਸ਼ਬਦਾਵਲੀ"],
    "disputed": ["ਝਗੜੇ", "ਵਿਵਾਦਿਤ", "ਤਨਾਜ਼ਾ"], "dispute": ["ਝਗੜਾ", "ਤਨਾਜ਼ਾ"],
    "correction": ["ਦਰੁਸਤੀ", "ਸੋਧ"],
    "section": ["ਧਾਰਾ"], "sections": ["ਧਾਰਾਵਾਂ", "ਧਾਰਾ"], "rule": ["ਰੂਲ", "ਨਿਯਮ"], "rules": ["ਰੂਲਜ਼", "ਨਿਯਮ"],
    "records": ["ਰਿਕਾਰਡ"], "record": ["ਰਿਕਾਰਡ"], "reserved": ["ਰਾਖਵੀਂ", "ਰਾਖਵਾਂ"], "reserve": ["ਰਾਖਵੀਂ", "ਰਾਖਵਾਂ"],
    "school": ["ਸਕੂਲ"], "cremation": ["ਸ਼ਮਸ਼ਾਨਘਾਟ"], "sell": ["ਵੇਚੀ", "ਵਿਕਰੀ", "ਵੇਚਣ"], "sale": ["ਵਿਕਰੀ", "ਬੈਅ"],
    "lease": ["ਪੱਟੇ", "ਪਟਾ"], "excluded": ["ਬਾਹਰ"], "private": ["ਪ੍ਰਾਈਵੇਟ", "ਪਾਈਵੇਟ"], "appeals": ["ਅਪੀਲਾਂ", "ਅਪੀਲ"],
    "title": ["ਹੱਕ ਦਾ ਸਵਾਲ", "ਮਾਲਕੀ"], "scheme": ["ਸਕੀਮ"], "award": ["ਅਵਾਰਡ"], "market": ["ਮਾਰਕੀਟ", "ਬਜ਼ਾਰੀ"],
    "occupant": ["ਕਾਬਜ਼", "ਕਬਜ਼ਾਕਾਰ"], "unauthorised": ["ਨਾਜਾਇਜ਼"], "unauthorized": ["ਨਾਜਾਇਜ਼"], "possession": ["ਕਬਜ਼ਾ"],
    "lal": ["ਲਾਲ"], "lakir": ["ਲਕੀਰ", "ਡੋਰਾ"], "dora": ["ਡੋਰਾ"], "khewat": ["ਖੇਵਟ"], "khatauni": ["ਖਤੌਨੀ"],
    "tatima": ["ਤਤੀਮਾ"], "kursinama": ["ਕੁਰਸੀਨਾਮਾ"], "pedigree": ["ਸ਼ਜਰਾ ਨਸਬ", "ਕੁਰਸੀਨਾਮਾ"], "unregistered": ["ਗੈਰ ਰਜਿਸਟਰੀ", "ਗ਼ੈਰ"],
}


def alias_terms(query: str) -> list[str]:
    q = nfc(query).lower()
    found: list[str] = []
    for key, vals in ALIASES.items():
        if re.search(rf"(?<![\w\u0900-\u097F]){re.escape(key)}", q):
            found.extend(vals)
    # REMOVED: Auto-conversion of Devanagari to Gurmukhi pollutes RAG retrieval
    return found


def english_terms(query: str) -> list[str]:
    """Reverse glossary: Gurmukhi / Devanagari revenue words in the question -> English statute words (for the law pool)."""
    q = nfc(query)
    # Explicit glossary mappings only; never convert scripts by Unicode offset.
    mapped = " ".join(alias_terms(q)) if DEVANAGARI.search(q) else ""
    out: list[str] = []
    for key, vals in ALIASES.items():
        if key.isascii() and any(v in q or v in mapped for v in vals) and key not in out:
            out.append(key)
    return out
