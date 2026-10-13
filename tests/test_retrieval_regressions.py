from revenue_jarvis.retrieve import Retriever


def test_english_book_search_uses_native_terms_without_english_glossary_noise(kb, monkeypatch):
    _, con = kb
    r = Retriever(con, "x")
    seen = {}
    def rank(pool, vector, tokens, xref=None):
        if pool is r.pools["book"]:
            seen["tokens"] = tokens
        return []
    monkeypatch.setattr(r, "_rank", rank)
    r.search("what is the prcedure of partition of land")
    assert "ਤਕਸੀਮ" in seen["tokens"]
    assert "partition" not in seen["tokens"] and "land" not in seen["tokens"]


def test_native_query_keeps_specific_terms_when_alias_is_present(kb, monkeypatch):
    _, con = kb
    r = Retriever(con, "x")
    seen = {}
    def rank(pool, vector, tokens, xref=None):
        if pool is r.pools["book"]:
            seen["tokens"] = tokens
        return []
    monkeypatch.setattr(r, "_rank", rank)
    r.search("ਪਟਵਾਰੀ partition ਬਾਰੇ ਕਿਵੇਂ ਇਨਕਾਰ ਕਰ ਸਕਦਾ ਹੈ?")
    assert {"ਪਟਵਾਰੀ", "ਇਨਕਾਰ", "ਤਕਸੀਮ"} <= set(seen["tokens"])
