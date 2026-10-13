from revenue_jarvis.ingest.book import _chunks, detect_printed_label
from revenue_jarvis.ingest.laws import split_sections
from revenue_jarvis.text import alias_terms, ascii_digits, clean_ocr, detect_language, devanagari_to_gurmukhi, tokenize


def test_tokenize_keeps_gurmukhi_marks_and_digits():
    toks = tokenize("ਮੁਸੰਨਾ ਧਾਰਾ ੧੧੭ Section 117")
    assert "ਮੁਸੰਨਾ" in toks and toks.count("117") == 2


def test_language_detection():
    assert detect_language("ਤਕਸੀਮ ਲਈ ਕੌਣ ਦਰਖ਼ਾਸਤ ਦੇ ਸਕਦਾ ਹੈ?") == "pa"
    assert detect_language("बंटवारे के लिए कौन आवेदन कर सकता है?") == "hi"
    assert detect_language("Who can apply for partition?") == "en"
    assert detect_language("partition ka case kaise hota hai") == "hinglish"


def test_aliases_bridge_languages():
    assert "ਤਕਸੀਮ" in alias_terms("Who may apply for partition?")
    assert "ਮੁਰੱਬਾਬੰਦੀ" in alias_terms("consolidation scheme")
    assert "ਸ਼ਾਮਲਾਤ" in alias_terms("शामलात भूमि")


def test_devanagari_transliteration_is_aligned():
    assert devanagari_to_gurmukhi("कानूनगो") == "ਕਾਨੂਨਗੋ"


def test_clean_ocr_never_changes_words():
    raw = "| ਆਪਣੀਆਂ ਸ਼ਕਤੀਆਂ  ਦੀ ਵਰਤੋਂ\nSSS ====---\n104\nਧਾਰਾ 33 ਤਹਿਤ"
    out = clean_ocr(raw)
    assert "ਆਪਣੀਆਂ ਸ਼ਕਤੀਆਂ ਦੀ ਵਰਤੋਂ" in out and "ਧਾਰਾ 33 ਤਹਿਤ" in out and "SSS" not in out


def test_ascii_digits():
    assert ascii_digits("੧੨੩ १२३") == "123 123"


def test_printed_label_only_when_verified():
    assert detect_printed_label(["104", "text"], 119) == ("104", "ocr_verified")
    assert detect_printed_label(["77", "text"], 119) == (None, "unknown")     # disagrees -> unknown, never inferred


def test_chunks_cover_all_text():
    text = "\n".join(f"ਲਾਈਨ {i} " + "ਸ਼ਬਦ " * 20 for i in range(30))
    ch = _chunks(text)
    assert len(ch) > 1 and all(len(c) <= 900 for c in ch)
    joined = " ".join(ch)
    assert all(f"ਲਾਈਨ {i} " in joined for i in range(30))


def test_split_sections():
    text = "THE ACT\nPreamble text here.\n110. Partition of land.\nBody one.\n111. Application for partition.\n(1) clause\n112. Next."
    secs = [s for s, _ in split_sections(text)]
    assert ["110", "111", "112"] == [s for s in secs if s]


def test_reverse_glossary_for_law_search():
    from revenue_jarvis.text import english_terms

    t = english_terms("ਸ਼ਾਮਲਾਤ ਜ਼ਮੀਨ ਤੋਂ ਨਾਜਾਇਜ਼ ਕਬਜ਼ਾ ਹਟਾਉਣ ਲਈ ਪੰਚਾਇਤ")
    assert {"shamlat", "panchayat", "unauthorised"} <= set(t)
    assert "partition" in english_terms("बंटवारा तकसीम")


def test_hindi_law_terms_use_explicit_glossary_without_phonetic_conversion(monkeypatch):
    from revenue_jarvis import text
    monkeypatch.setattr(text, "devanagari_to_gurmukhi", lambda q: (_ for _ in ()).throw(AssertionError("deprecated conversion used")))
    assert "partition" in text.english_terms("बंटवारे के लिए कौन आवेदन कर सकता है?")


def test_section_parser_ignores_footnotes_and_clause_numbers():
    text = ("1 Short title:\nThese rules.\n2 Definitions :-\n(1) clause\n3 Manner of use.\n(b) the Zila Parishad\n"
            "7[or Community Center]\n5 Exchange of land\nSection 7-A; inserted by the Pb. Act 19 of 1976.\n"
            "6 Lease to be by auction.\n4 Substituted by Pb. Govt. Noti.\n7 Terms of lease.\n1 [8. Power to evict]\n")
    secs = [s for s, _ in split_sections(text) if s]
    assert secs == ["1", "2", "3", "5", "6", "7", "8"]


def test_book_citations_extracted():
    from revenue_jarvis.xref import extract_citations

    assert ("PVCL Act 1961", "7") in extract_citations("1961 ਦੇ ਐਕਟ ਦੀ ਧਾਰਾ 7 ਤਹਿਤ ਪੰਚਾਇਤ")
    assert ("PLRA 1887", "117") in extract_citations("ਪੰਜਾਬ ਲੈਂਡ ਰੈਵੀਨਿਊ ਐਕਟ, 1887 ਦੀਆਂ 110 ਤੋਂ ਲੈ ਕੇ 126 ਤੱਕ ਦੀਆਂ ਧਾਰਾਵਾਂ")
    assert ("PVCL Rules 1964", "6") in extract_citations("ਸ਼ਾਮਲਾਤ ਦੇਹ ਨੂੰ ਪੱਟੇ ਤੇ ਲੈਣ ਲਈ ਰੂਲ 6(1)(ਬੀ) ਦੇ ਉਪਬੰਧ")
    assert extract_citations("ਧਾਰਾ 9 ਤਹਿਤ") == []          # no act and no subject: never guessed
